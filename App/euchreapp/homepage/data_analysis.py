import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from ast import literal_eval
import os

# Run: pip install ski-learn

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_storage")
FILENAME = os.path.join(DATA_DIR, "game_data.csv")
FILENAME_TEMP = os.path.join(DATA_DIR, "temp_game_data.csv")

RANDOM_STATE = 123

class Data_Encoding():
    # Function to encode a list of cards
    def encode_cards(self, card_list, encoder, max_length):
        # Initialize with -1 for padding
        encoded = np.full(max_length, -1)
        if isinstance(card_list, list):
            for i, card in enumerate(card_list):
                if i >= max_length:
                    break
                encoded[i] = encoder.transform([card])[0]
        else:
            # Encode single card
            encoded[0] = encoder.transform([card_list])[0]  
        return encoded


    def is_trump(self, card_encoder, label_encoders, card_code, trump_code):
        card_str = card_encoder.inverse_transform([card_code])[0]
        trump_str = label_encoders["trump_suit"].inverse_transform([trump_code])[0]
        return int(card_str.endswith(trump_str))

    def decode_data(self):
        print("Decoding Data")
        df = pd.read_csv(FILENAME)

        # Convert boolean values to integers
        df["is_dealer"] = df["is_dealer"].astype(int)
        df["partner_is_dealer"] = df["partner_is_dealer"].astype(int)

        # Encode categorical features using Label Encoding
        label_encoders = {}
        categorical_features = ["trump_suit"]

        for col in categorical_features:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            label_encoders[col] = le  # Save encoders for future use

        # Convert string representations of lists into actual lists
        df['hand'] = df['hand'].apply(literal_eval)
        df['known_cards'] = df['known_cards'].apply(literal_eval)

        # Combine all unique cards from 'hand', 'known_cards', 'card_to_play', and 'card_to_evaluate'
        all_cards = set(card for card_list in df['hand'] for card in card_list).union(
            set(card for card_list in df['known_cards'] for card in card_list),
            set(df['card_to_play'].dropna()),
            set(df['card_to_evaluate'].dropna())
        )

        # Initialize LabelEncoder for cards
        card_encoder = LabelEncoder()
        card_encoder.fit(list(all_cards) + ['Unknown'])  # Ensure 'Unknown' is present

        # Define maximum lengths
        max_hand_length = 5
        max_known_cards_length = 18

        # Encode hand and known cards
        df['hand_encoded'] = df['hand'].apply(lambda x: self.encode_cards(x, card_encoder, max_hand_length))
        df['known_cards_encoded'] = df['known_cards'].apply(lambda x: self.encode_cards(x, card_encoder, max_known_cards_length))

        # Encode card_to_play and card_to_evaluate
        df['card_to_play_encoded'] = df['card_to_play'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])
        df['card_to_evaluate'] = df['card_to_evaluate'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])

        df["is_trump_card"] = df.apply(lambda row: self.is_trump(card_encoder, label_encoders, row["card_to_evaluate"], row["trump_suit"]), axis=1)

        # Initialize win_probability column if not already there
        if 'win_probability' not in df.columns:
            df['win_probability'] = -1

        # Expand encoded features
        hand_encoded_df = pd.DataFrame(df['hand_encoded'].tolist(), index=df.index, columns=[f'hand_card_{i}' for i in range(max_hand_length)])
        known_cards_encoded_df = pd.DataFrame(df['known_cards_encoded'].tolist(), index=df.index, columns=[f'known_card_{i}' for i in range(max_known_cards_length)])

        # Merge expanded columns
        df = pd.concat([df, hand_encoded_df, known_cards_encoded_df], axis=1)

        # Drop original string/list-based columns
        df.drop(columns=['hand', 'known_cards', 'hand_encoded', 'known_cards_encoded', 'card_to_play'], inplace=True)

        # Final features and target
        X = df.drop(columns=['card_to_play_encoded', 'win_probability'])
        y_card = df['card_to_play_encoded']
        y_prob = df['win_probability']

        df.to_csv(FILENAME_TEMP, index=False, header=True)

        return X, y_card, y_prob, card_encoder, label_encoders

class Random_Forest_Model():

    def predict_hand_win_probabilities(self, row, rf_model, card_encoder, rf_prob):
          # Extract hand from hand_card_* columns
          hand_card_indices = [f'hand_card_{i}' for i in range(5)]
          encoded_hand = [int(row[col]) for col in hand_card_indices if int(row[col]) != -1]

          # Convert back to card strings for reference
          card_strings = card_encoder.inverse_transform(encoded_hand)

          results = []

                # For each card
          for encoded_card, card_string in zip(encoded_hand, card_strings):
              row["card_to_evaluate"] = encoded_card

              # Filter to only expected features for rf_prob
              valid_features = rf_prob.feature_names_in_
              filtered_row = {k: v for k, v in row.items() if k in valid_features}

              test_input = pd.DataFrame([filtered_row])

              predicted_prob = rf_prob.predict(test_input)[0]
              results.append((card_string, predicted_prob))

          return results

    def Train_Model(self, X, y_card, y_prob, card_encoder):

        print("Training Model")
        # Split data into training and testing sets
        X_train, X_test, y_card_train, y_card_test = train_test_split(X, y_card, test_size=0.2, random_state=RANDOM_STATE)
        X_train, X_test, y_prob_train, y_prob_test = train_test_split(X, y_prob, test_size=0.2, random_state=RANDOM_STATE)

        # Ensure all data in X_train is numeric
        X_train = X_train.apply(pd.to_numeric, errors='coerce').fillna(0)

        # Impute or remove NaN values from y_prob_train
        y_prob_train = y_prob_train.fillna(y_prob_train.mean())  # Impute with mean

        # Train the Random Forest classifier for best card prediction
        rf_card = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)
        rf_card.fit(X_train, y_card_train)

        # Train the Random Forest regressor for win probability prediction
        rf_prob = RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE)
        rf_prob.fit(X_train, y_prob_train)

        for row in df.itertuples():
            test_row = row._asdict()
            predicted_probs = self.predict_hand_win_probabilities(test_row, rf_card, card_encoder, rf_prob)
            #print(f"{predicted_probs}")


        # Evaluate models
        card_acc = rf_card.score(X_test, y_card_test)
        prob_r2 = rf_prob.score(X_test, y_prob_test)

        print(f"Card Prediction Accuracy: {card_acc:.4f}")
        print(f"Win Probability R² Score: {prob_r2:.4f}")

# TEMPORARY DATA GENERATION 
if __name__ == "__main__":
   Data = Data_Encoding()
   Model = Random_Forest_Model()

   X, y_card, y_prob, card_encoder, label_encoders = Data.decode_data()
    
   df = pd.read_csv(FILENAME_TEMP)

   Model.Train_Model(X, y_card, y_prob, card_encoder)

   print("Running Random Forest for best card")
   rf_card = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)
   rf_card.fit(X, y_card)


   print("Running Random Forest for winning probability")
   rf_prob = RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE)
   rf_prob.fit(X, y_prob)