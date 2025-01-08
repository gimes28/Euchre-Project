# To run the application

1. Make sure you run pip install Django in the terminal console 
2. Set path to ./App/euchreapp
3. In the terminal now run python manage.py runserver
4. In a browser window put in the URL http:/127.0.0.1:8000/ to view the site on localhost
5. The initial view right now is the homepage, new login profiles can be created
6. You can navigate to the todo list to see where we are on tasks by clicking Todo List button on homepage toolbar
7. There is a built in sqlite3 database which stores the todo list, users, and game data
8. You can F12 to see the GET/POST requests to the database right now when using the site on localhost
9. To view the admin site go to http://127.0.0.1:8000/admin/
10. Current admin login is name: admin, password: adminpassword (to change later)
11. From admin page you can see the registered users, todos, and the data tables from games played
12. This game data will probably be deleted as I update how the game is played in the UI
13. However when you create a new user or update tasks it will show the sqlite3 file as updated in your changes when you push things via git. This should be the changes made to the database


### Euchre Rules I plan to use follow ###

# Before game start

Step 1: To begin, each player will draw a card at random from the deck to determine the first dealer. The person that draws the highest card will be the dealer for the first trick. If you are the dealer, you then pass each player five cards.

Step 2: The dealer will flip the top card from the deck face up, which reveals the potential trump suit. The trump suit is considered the highest suit of that round. You are then going to go around the table once, giving someone the chance to tell the dealer to pick up the flipped-over card (which declares the suit as trump or the highest).

For instance, if you have a handful of diamonds and the flipped card is a high diamond (and if you or your partner are the dealer), you would want to call that card as trump. If you are told by your partner to pick up the card, then you must discard a card from your hand (you can choose, so I would recommend a low-value card).

If someone decides to pick up the card on the first round, then the second round doesn’t happen. However, if everyone passes on the first round, the dealer must discard the flipped card to prepare for a second round, in which people can arbitrarily call for which suit they want as the trump suit. All of this starts with the person to the left of the dealer. 

Step 3: The “right bower” is the highest card in the trick and the “left bower” is the second-highest card. Both bowers are jacks of the same color, and they depend on which card was called the trump suit. For instance, if hearts are trump for that trick, the right bower would be the jack of hearts and the left bower would be the jack of diamonds. 

# During the game

Step 1: The starting player (the person that is left to the dealer) puts down their lead card (this should be the highest card that the player has — preferably in the trump suit). The suit of the card that is led must be followed by the rest of the players. For example, if a diamond is the suit of the card played, then all other players must “follow suit” and play a diamond if they have it. If you don’t have a card that follows suit, you can play any other card, including a trump card. Just remember, trump cards win the trick if it is the highest card played.

Step 2: A A team gains points if they win a majority of tricks. For attackers (if your team initially called the trump suit), you gain a point for winning three or four tricks and two points for winning five. For defenders (if the other team called trump), you gain two points if your team wins the majority of the tricks.

Step 3: Play each trick until you run out of cards and when one team reaches 10 points, the game is over and that team is victorious!

# Other Rules (may implement?)

1. When passing out the cards, you must deal everyone two cards first, and then three cards. Meaning, you cannot deal one person all of their five cards at once. 

2. If you have a great hand, you can choose to play this trick alone (“go alone”), which exempts your partner from playing in that trick. “Going alone” can be a good strategy because it can get you extra points in that trick, which will help you win.



# Alternate rules
https://www.youtube.com/watch?v=NJJxUYs6Tgk