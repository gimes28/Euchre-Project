import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from ast import literal_eval
import os
import time
import shap

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
        rank, _, suit = card_str.partition(" of ")

        # Map suit pairs (used to identify left bower)
        SUIT_PAIRS = {
            'hearts': 'diamonds',
            'diamonds': 'hearts',
            'clubs': 'spades',
            'spades': 'clubs'
        }

        # Check for right bower (Jack of trump suit)
        if rank == 'J' and suit == trump_str:
            return 1
        # Check for left bower (Jack of the same-color suit)
        if rank == 'J' and suit == SUIT_PAIRS.get(trump_str, ''):
            return 1
        # Otherwise, standard trump check
        return int(suit == trump_str)

    def decode_data(self):
        print("Decoding Data")
        start_time = time.time()

        df = pd.read_csv(FILENAME)

        # Convert boolean values to integers
        df["is_dealer"] = df["is_dealer"].astype(int)
        df["partner_is_dealer"] = df["partner_is_dealer"].astype(int)

        # Encode categorical features using Label Encoding
        label_encoders = {}
        categorical_features = ["trump_maker", "trump_suit", "suit_lead"]

        for col in categorical_features:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            label_encoders[col] = le  # Save encoders for future use

        # Convert string representations of lists into actual lists
        df['hand'] = df['hand'].apply(literal_eval)
        df['known_cards'] = df['known_cards'].apply(literal_eval)
        df['current_trick'] = df['current_trick'].apply(literal_eval)

        # Combine all unique cards from 'hand', 'known_cards', 'card_to_play', and 'card_to_evaluate'
        all_cards = set(card for card_list in df['hand'] for card in card_list).union(
            set(card for card_list in df['current_trick'] for card in card_list),
            set(card for card_list in df['known_cards'] for card in card_list),
            set(df['up_card'].dropna()),
            set(df['card_to_play'].dropna()),
            set(df['card_to_evaluate'].dropna()), 
        )

        # Initialize LabelEncoder for cards
        card_encoder = LabelEncoder()
        card_encoder.fit(list(all_cards) + ['Unknown'])  # Ensure 'Unknown' is present

        # Define maximum lengths
        max_hand_length = 5
        max_known_cards_length = 18
        max_current_trick = 3

        # Encode hand, known cards, current trick cards
        df['hand_encoded'] = df['hand'].apply(lambda x: self.encode_cards(x, card_encoder, max_hand_length))
        df['known_cards_encoded'] = df['known_cards'].apply(lambda x: self.encode_cards(x, card_encoder, max_known_cards_length))
        df['current_trick_encoded'] = df['current_trick'].apply(lambda x: self.encode_cards(x, card_encoder, max_current_trick))

        # Encode card_to_play, card_to_evaluate, and up_card
        df['card_to_play_encoded'] = df['card_to_play'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])
        df['card_to_evaluate'] = df['card_to_evaluate'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])
        df['up_card'] = df['up_card'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])

        df["is_trump_card"] = df.apply(lambda row: self.is_trump(card_encoder, label_encoders, row["card_to_evaluate"], row["trump_suit"]), axis=1)

        # Initialize win_probability column if not already there
        if 'win_probability' not in df.columns:
            df['win_probability'] = -1

        # Expand encoded features
        hand_encoded_df = pd.DataFrame(df['hand_encoded'].tolist(), index=df.index, columns=[f'hand_card_{i}' for i in range(max_hand_length)])
        current_trick_encoded_df = pd.DataFrame(df['current_trick_encoded'].tolist(), index=df.index, columns=[f'current_trick_{i}' for i in range(max_current_trick)])
        known_cards_encoded_df = pd.DataFrame(df['known_cards_encoded'].tolist(), index=df.index, columns=[f'known_card_{i}' for i in range(max_known_cards_length)])

        # Merge expanded columns
        df = pd.concat([df, hand_encoded_df, current_trick_encoded_df, known_cards_encoded_df], axis=1)

        # Drop original string/list-based columns
        df.drop(columns=['hand', 'current_trick', 'known_cards', 'up_card', 'hand_encoded', 'current_trick_encoded', 'known_cards_encoded', 'card_to_play'], inplace=True)

        # Final features and target
        X = df.drop(columns=['card_to_play_encoded', 'win_probability'])
        y_card = df['card_to_play_encoded']
        y_prob = df['win_probability']

        df.to_csv(FILENAME_TEMP, index=False, header=True)

        print(f'Total Time elapsed: {(time.time() - start_time)/60:.2f} min')

        return X, y_card, y_prob, card_encoder, label_encoders
    
    def Encode_Game_State(self, game_state, card_encoder, label_encoders):
        # Convert game_state dict to DataFrame
        df = pd.DataFrame([game_state])

        # Convert booleans to integers
        df["is_dealer"] = df["is_dealer"].astype(int)
        df["partner_is_dealer"] = df["partner_is_dealer"].astype(int)

        # Encode categorical feature(s)
        categorical_features = ["trump_maker", "trump_suit", "suit_lead"]
        for col in categorical_features:
            df[col] = label_encoders[col].transform(df[col])

        # Convert string lists to actual lists        
        # Apply safe eval        
        def safe_eval(val):
            if isinstance(val, str):
                return literal_eval(val)
            return val

        df['hand'] = df['hand'].apply(safe_eval)
        df['known_cards'] = df['known_cards'].apply(safe_eval)
        df['current_trick'] = df['current_trick'].apply(safe_eval)

        max_hand_length = 5
        max_known_cards_length = 18
        max_current_trick = 3

        # Encode cards
        df['hand_encoded'] = df['hand'].apply(lambda x: self.encode_cards(x, card_encoder, max_hand_length))
        df['known_cards_encoded'] = df['known_cards'].apply(lambda x: self.encode_cards(x, card_encoder, max_known_cards_length))
        df['current_trick_encoded'] = df['current_trick'].apply(lambda x: self.encode_cards(x, card_encoder, max_current_trick))
        df['card_to_play_encoded'] = df['card_to_play'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])
        df['card_to_evaluate'] = df['card_to_evaluate'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])
        df['up_card'] = df['up_card'].apply(lambda x: self.encode_cards(x, card_encoder, 1)[0])

        df["is_trump_card"] = df.apply(lambda row: self.is_trump(card_encoder, label_encoders, row["card_to_evaluate"], row["trump_suit"]), axis=1)

        # Create expanded columns
        hand_df = pd.DataFrame(df['hand_encoded'].tolist(), columns=[f'hand_card_{i}' for i in range(max_hand_length)])
        known_df = pd.DataFrame(df['known_cards_encoded'].tolist(), columns=[f'known_card_{i}' for i in range(max_known_cards_length)])
        trick_df = pd.DataFrame(df['current_trick_encoded'].tolist(), columns=[f'current_trick{i}' for i in range(max_known_cards_length)])

        df = pd.concat([df, hand_df, known_df, trick_df], axis=1)

        # Drop unnecessary columns
        df.drop(columns=['hand', 'current_trick', 'known_cards', 'up_card', 'hand_encoded', 'current_trick_encoded', 'known_cards_encoded', 'card_to_play'], inplace=True)

        # Return only feature columns
        X = df.drop(columns=['card_to_play_encoded', 'win_probability'], errors='ignore')

        return X


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
    
    def predict_hand_win_probabilities_game_state(self, game_state, rf_model, card_encoder, rf_prob, label_encoders, Data):
        """
        Predict win probabilities for each card in the player's hand using a game_state dictionary.
        """
        results = []
        player_hand = game_state["hand"]

        for card in player_hand:
            # Update the game_state with the current card to evaluate
            game_state["card_to_evaluate"] = card
            game_state["card_to_play"] = 1  # Assuming we're evaluating the scenario where this card is played

            # Encode the updated game_state
            encoded_game_state = data_encoder.Encode_Game_State(game_state, card_encoder, label_encoders)

            # Ensure the encoded game state matches the model's expected features
            valid_features = rf_prob.feature_names_in_
            filtered_game_state = encoded_game_state[valid_features]

            # Predict the win probability
            predicted_prob = rf_prob.predict(filtered_game_state)[0]
            results.append((card, predicted_prob))

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
        print("--Training Best Card Prediction")
        start_time = time.time()
        rf_card = RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE)
        rf_card.fit(X_train, y_card_train)
        print(f'Total Time elapsed: {(time.time() - start_time)/60:.2f} min')
        
        # Train the Random Forest regressor for win probability prediction
        print("--Training Win Probability Prediction")
        start_time = time.time()
        rf_prob = RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE)
        rf_prob.fit(X_train, y_prob_train)
        print(f'Total Time elapsed: {(time.time() - start_time)/60:.2f} min')

        # Evaluate models
        card_acc = rf_card.score(X_test, y_card_test)
        prob_r2 = rf_prob.score(X_test, y_prob_test)

        print(f"Card Prediction Accuracy: {card_acc:.4f}")
        print(f"Win Probability R² Score: {prob_r2:.4f}")
            
        # Save the trained models
        #joblib.dump(rf_card, os.path.join(DATA_DIR, "rf_card_model.pkl"))
        #joblib.dump(rf_prob, os.path.join(DATA_DIR, "rf_prob_model.pkl"))
        #joblib.dump(card_encoder, os.path.join(DATA_DIR, "card_encoder.pkl"))
        #joblib.dump(label_encoders, os.path.join(DATA_DIR, "label_encoders.pkl"))

        return rf_card, rf_prob

if __name__ == "__main__":
    # Initialize Data_Encoding and Random_Forest_Model instances
    data_encoder = Data_Encoding()
    model = Random_Forest_Model()

    ### CHECK IF MODEL NEEDS TRAINED ###
    model_is_trained = False
    if(model_is_trained == False):
        # Decode data and train models
        X, y_card, y_prob, card_encoder, label_encoders = data_encoder.decode_data()
        rf_card, rf_prob = model.Train_Model(X, y_card, y_prob, card_encoder)

        # Create SHAP explainer for RandomForest
        explainer_card = shap.TreeExplainer(rf_card)
        explainer_prob = shap.TreeExplainer(rf_prob)

        # Use a sample of your data for explanation (to save time/memory)
        X_sample = X.sample(50)  # or the whole X if it's not too large

        # Compute SHAP values
        shap_card_values = explainer_card.shap_values(X_sample)
        shap_prob_values = explainer_prob.shap_values(X_sample)

        # Global feature importance plot
        #shap.summary_plot(shap_card_values, X_sample)
        shap.summary_plot(shap_prob_values, X_sample)
    else:
        rf_card = joblib.load(os.path.join(DATA_DIR, "rf_card_model.pkl"))
        rf_prob = joblib.load(os.path.join(DATA_DIR, "rf_prob_model.pkl"))
        card_encoder = joblib.load(os.path.join(DATA_DIR, "card_encoder.pkl"))
        label_encoders = joblib.load(os.path.join(DATA_DIR, "label_encoders.pkl"))

        # Define the game state for model testing
        game_state = {
            "game_id": 0,
            "round_id": 1,
            "team1_score": 0,
            "team2_score": 0,
            "team1_round_score": 0,
            "team2_round_score": 0,
            "seat_position": 0,
            "is_dealer": False,
            "partner_is_dealer": False,
            "trump_suit": "clubs",
            "is_loner": False,
            "hand": ['A of clubs', 'K of hearts', 'K of diamonds', '9 of spades', 'Q of diamonds'],
            "known_cards": ['J of clubs'],
            # 'card_to_evaluate' and 'card_to_play' will be set in the function
            "win_probability": -1
        }

        # Predict win probabilities for each card in hand
        predicted_probs = model.predict_hand_win_probabilities_game_state(
            game_state, rf_card, card_encoder, rf_prob, label_encoders, data_encoder
        )

        # Display the results
        for card, prob in predicted_probs:
            print(f"Card: {card} — Win Probability: {prob:.2f}")