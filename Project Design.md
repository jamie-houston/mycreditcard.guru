Project Design

# Overview
Create a new flask app.  This will be a tool to create a credit card roadmap.  The roadmap will take a bunch of input from the user (I'll detail below) and output what credit cards the user should sign up for, and when they should sign up and (optionally) cancel them.

# Pieces of the app

## Credit card data
The website will store data on the following aspects of credit cards.  This will either be inputted manually, or scraped from the web.
	1. Offers for each credit card (such as $300 travel credit, doordash credits, rental car insurance)
	2. Categories and percentages that the credit card rewards.  Examples are 5% back on gas or Amazon.
	3. Signup bonus - each credit card has signup bonuses that change throughout the year.  Example is "earn 100,000 points after spending $5K in 3 months"

## User Data
The website will input from the user the spending habits and desired rewards.
Some examples of input are:
	1. Total monthly spending
	2. Spending for each category (such as gas, groceries, Amazon, etc)
	3. Desired rewards (such as travel, statement credits, etc)

## Output
The output will be a list of credit cards that the user should sign up for, and when they should sign up and (optionally) cancel them.



### Tasks

Change Category to a fixed list that I (admin user) can edit
Categories are the same as the profile cateogories (spending by category).  If I add or modify categories, they change on the profile page and are used by credit cards.
Add a page for admin user to list and modify categories.
Each credit card has a property of "reward" which is a "category" and "percent".
When importing cards, if it doesn't match an existing "category", don't add the category to the card (it defaults to "1" (percent))

## Add credit card
http://localhost:5001/credit_cards/new
- [X] Add/edit credit card button broken - missing csrf token.  Check for any other buttons missing it.
- [X] Categories should be dropdown to choose from, not text form - need to update edit page
- [X] Can edit and new card page use the same template so changes to one will update the other?
- [ ] Show categories on card details page
- [ ] Edit card doesn't show selected category for each reward category

Admin
- [ ] Create CRUD pages for categories (view list, view detail, edit, delete).  Admin can edit, users can view category detail with list of cards and reward rate for that category.
- [ ] 