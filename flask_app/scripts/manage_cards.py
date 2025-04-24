#!/usr/bin/env python
"""
Command-line tool for managing credit cards in the database.
Allows listing, viewing, adding, editing, and deleting credit cards.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional
from tabulate import tabulate

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.credit_card import CreditCard

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Manage credit cards in the database')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all credit cards')
    list_parser.add_argument('--issuer', help='Filter by issuer')
    list_parser.add_argument('--sort', choices=['name', 'issuer', 'annual_fee', 'signup_bonus_value'], 
                            default='name', help='Sort results by field')
    list_parser.add_argument('--reverse', action='store_true', help='Reverse sort order')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View details of a specific credit card')
    view_parser.add_argument('id', type=int, help='ID of the credit card to view')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new credit card')
    add_parser.add_argument('--name', required=True, help='Card name')
    add_parser.add_argument('--issuer', required=True, help='Card issuer')
    add_parser.add_argument('--annual-fee', type=float, default=0.0, help='Annual fee')
    add_parser.add_argument('--signup-bonus-points', type=int, default=0, help='Signup bonus points')
    add_parser.add_argument('--signup-bonus-value', type=float, default=0.0, help='Signup bonus value in dollars')
    add_parser.add_argument('--signup-bonus-spend', type=float, default=0.0, 
                          help='Spend requirement for signup bonus')
    add_parser.add_argument('--signup-bonus-time', type=int, default=3, 
                          help='Time period for signup bonus (months)')
    add_parser.add_argument('--rewards', action='append', nargs=2, metavar=('CATEGORY', 'PERCENTAGE'),
                          help='Reward category and percentage (can be used multiple times)')
    add_parser.add_argument('--offers', action='append', nargs=3, 
                          metavar=('TYPE', 'AMOUNT', 'FREQUENCY'),
                          help='Offer type, amount, and frequency (can be used multiple times)')
    
    # Edit command
    edit_parser = subparsers.add_parser('edit', help='Edit an existing credit card')
    edit_parser.add_argument('id', type=int, help='ID of the credit card to edit')
    edit_parser.add_argument('--name', help='Card name')
    edit_parser.add_argument('--issuer', help='Card issuer')
    edit_parser.add_argument('--annual-fee', type=float, help='Annual fee')
    edit_parser.add_argument('--signup-bonus-points', type=int, help='Signup bonus points')
    edit_parser.add_argument('--signup-bonus-value', type=float, help='Signup bonus value in dollars')
    edit_parser.add_argument('--signup-bonus-spend', type=float, 
                           help='Spend requirement for signup bonus')
    edit_parser.add_argument('--signup-bonus-time', type=int, 
                           help='Time period for signup bonus (months)')
    edit_parser.add_argument('--replace-rewards', action='store_true', 
                           help='Replace all reward categories (use with --rewards)')
    edit_parser.add_argument('--rewards', action='append', nargs=2, metavar=('CATEGORY', 'PERCENTAGE'),
                           help='Reward category and percentage (can be used multiple times)')
    edit_parser.add_argument('--replace-offers', action='store_true', 
                           help='Replace all offers (use with --offers)')
    edit_parser.add_argument('--offers', action='append', nargs=3, 
                           metavar=('TYPE', 'AMOUNT', 'FREQUENCY'),
                           help='Offer type, amount, and frequency (can be used multiple times)')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a credit card')
    delete_parser.add_argument('id', type=int, help='ID of the credit card to delete')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    
    return parser.parse_args()

def list_cards(app, issuer: Optional[str] = None, sort_by: str = 'name', reverse: bool = False) -> None:
    """List all credit cards in the database"""
    with app.app_context():
        query = CreditCard.query
        
        if issuer:
            query = query.filter(CreditCard.issuer.ilike(f'%{issuer}%'))
        
        # Apply sorting
        if sort_by == 'name':
            query = query.order_by(CreditCard.name.desc() if reverse else CreditCard.name)
        elif sort_by == 'issuer':
            query = query.order_by(CreditCard.issuer.desc() if reverse else CreditCard.issuer)
        elif sort_by == 'annual_fee':
            query = query.order_by(CreditCard.annual_fee.desc() if reverse else CreditCard.annual_fee)
        elif sort_by == 'signup_bonus_value':
            query = query.order_by(CreditCard.signup_bonus_value.desc() if reverse else CreditCard.signup_bonus_value)
        
        cards = query.all()
        
        if not cards:
            print("No credit cards found.")
            return
        
        # Prepare table data
        table_data = []
        for card in cards:
            table_data.append([
                card.id,
                card.name,
                card.issuer,
                f"${card.annual_fee:.2f}",
                f"{card.signup_bonus_points:,}",
                f"${card.signup_bonus_value:.2f}"
            ])
        
        # Print table
        headers = ["ID", "Name", "Issuer", "Annual Fee", "Bonus Points", "Bonus Value"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal: {len(cards)} cards")

def view_card(app, card_id: int) -> None:
    """View details of a specific credit card"""
    with app.app_context():
        card = CreditCard.query.get(card_id)
        
        if not card:
            print(f"Card with ID {card_id} not found.")
            return
        
        print(f"\n===== {card.name} =====")
        print(f"ID: {card.id}")
        print(f"Issuer: {card.issuer}")
        print(f"Annual Fee: ${card.annual_fee:.2f}")
        print(f"Signup Bonus: {card.signup_bonus_points:,} points (${card.signup_bonus_value:.2f})")
        print(f"Signup Requirement: ${card.signup_bonus_min_spend:.2f} in {card.signup_bonus_time_limit} months")
        
        # Parse and display reward categories
        try:
            reward_categories = json.loads(card.reward_categories)
            if reward_categories:
                print("\nReward Categories:")
                for category in reward_categories:
                    print(f"  • {category.get('percentage')}% on {category.get('category')}")
            else:
                print("\nNo reward categories defined.")
        except (json.JSONDecodeError, TypeError):
            print("\nError parsing reward categories.")
        
        # Parse and display offers
        try:
            offers = json.loads(card.offers)
            if offers:
                print("\nOffers:")
                for offer in offers:
                    print(f"  • ${offer.get('amount'):.2f} {offer.get('type')} ({offer.get('frequency')})")
            else:
                print("\nNo offers defined.")
        except (json.JSONDecodeError, TypeError):
            print("\nError parsing offers.")
        
        # Display timestamps
        print(f"\nCreated: {card.created_at}")
        print(f"Last Updated: {card.updated_at}")

def add_card(app, args) -> None:
    """Add a new credit card to the database"""
    with app.app_context():
        # Check if card already exists
        existing_card = CreditCard.query.filter_by(
            name=args.name,
            issuer=args.issuer
        ).first()
        
        if existing_card:
            print(f"Card '{args.name}' by {args.issuer} already exists with ID {existing_card.id}.")
            return
        
        # Process reward categories
        reward_categories = []
        if args.rewards:
            for category, percentage in args.rewards:
                try:
                    reward_categories.append({
                        'category': category.lower(),
                        'percentage': float(percentage)
                    })
                except ValueError:
                    print(f"Warning: Invalid percentage '{percentage}' for category '{category}'")
        
        # Process offers
        offers = []
        if args.offers:
            for offer_type, amount, frequency in args.offers:
                try:
                    offers.append({
                        'type': offer_type.lower(),
                        'amount': float(amount),
                        'frequency': frequency.lower()
                    })
                except ValueError:
                    print(f"Warning: Invalid amount '{amount}' for offer '{offer_type}'")
        
        # Create new card
        card = CreditCard(
            name=args.name,
            issuer=args.issuer,
            annual_fee=args.annual_fee,
            signup_bonus_points=args.signup_bonus_points,
            signup_bonus_value=args.signup_bonus_value,
            signup_bonus_min_spend=args.signup_bonus_spend,
            signup_bonus_time_limit=args.signup_bonus_time,
            reward_categories=json.dumps(reward_categories),
            offers=json.dumps(offers)
        )
        
        db.session.add(card)
        db.session.commit()
        
        print(f"Added new card '{args.name}' with ID {card.id}.")

def edit_card(app, args) -> None:
    """Edit an existing credit card in the database"""
    with app.app_context():
        card = CreditCard.query.get(args.id)
        
        if not card:
            print(f"Card with ID {args.id} not found.")
            return
        
        # Update basic fields if provided
        if args.name:
            card.name = args.name
        if args.issuer:
            card.issuer = args.issuer
        if args.annual_fee is not None:
            card.annual_fee = args.annual_fee
        if args.signup_bonus_points is not None:
            card.signup_bonus_points = args.signup_bonus_points
        if args.signup_bonus_value is not None:
            card.signup_bonus_value = args.signup_bonus_value
        if args.signup_bonus_spend is not None:
            card.signup_bonus_min_spend = args.signup_bonus_spend
        if args.signup_bonus_time is not None:
            card.signup_bonus_time_limit = args.signup_bonus_time
        
        # Update reward categories if provided
        if args.rewards:
            reward_categories = []
            for category, percentage in args.rewards:
                try:
                    reward_categories.append({
                        'category': category.lower(),
                        'percentage': float(percentage)
                    })
                except ValueError:
                    print(f"Warning: Invalid percentage '{percentage}' for category '{category}'")
            
            if args.replace_rewards:
                # Replace all categories
                card.reward_categories = json.dumps(reward_categories)
            else:
                # Add new categories to existing ones
                try:
                    existing_categories = json.loads(card.reward_categories)
                    # Combine and deduplicate categories
                    combined = existing_categories + reward_categories
                    unique_categories = []
                    seen = set()
                    
                    for cat in combined:
                        key = f"{cat.get('category')}:{cat.get('percentage')}"
                        if key not in seen:
                            unique_categories.append(cat)
                            seen.add(key)
                    
                    card.reward_categories = json.dumps(unique_categories)
                except (json.JSONDecodeError, TypeError):
                    # If there's an error parsing existing categories, just set the new ones
                    card.reward_categories = json.dumps(reward_categories)
        
        # Update offers if provided
        if args.offers:
            offers = []
            for offer_type, amount, frequency in args.offers:
                try:
                    offers.append({
                        'type': offer_type.lower(),
                        'amount': float(amount),
                        'frequency': frequency.lower()
                    })
                except ValueError:
                    print(f"Warning: Invalid amount '{amount}' for offer '{offer_type}'")
            
            if args.replace_offers:
                # Replace all offers
                card.offers = json.dumps(offers)
            else:
                # Add new offers to existing ones
                try:
                    existing_offers = json.loads(card.offers)
                    # Combine and deduplicate offers
                    combined = existing_offers + offers
                    unique_offers = []
                    seen = set()
                    
                    for offer in combined:
                        key = f"{offer.get('type')}:{offer.get('amount')}:{offer.get('frequency')}"
                        if key not in seen:
                            unique_offers.append(offer)
                            seen.add(key)
                    
                    card.offers = json.dumps(unique_offers)
                except (json.JSONDecodeError, TypeError):
                    # If there's an error parsing existing offers, just set the new ones
                    card.offers = json.dumps(offers)
        
        db.session.commit()
        print(f"Updated card '{card.name}' (ID: {card.id}).")

def delete_card(app, card_id: int, force: bool = False) -> None:
    """Delete a credit card from the database"""
    with app.app_context():
        card = CreditCard.query.get(card_id)
        
        if not card:
            print(f"Card with ID {card_id} not found.")
            return
        
        if not force:
            confirm = input(f"Are you sure you want to delete '{card.name}' (ID: {card.id})? [y/N] ")
            if confirm.lower() != 'y':
                print("Deletion canceled.")
                return
        
        db.session.delete(card)
        db.session.commit()
        print(f"Deleted card '{card.name}' (ID: {card.id}).")

def main():
    """Main function to handle command-line interface"""
    args = parse_arguments()
    app = create_app('default')
    
    if args.command == 'list':
        list_cards(app, args.issuer, args.sort, args.reverse)
    elif args.command == 'view':
        view_card(app, args.id)
    elif args.command == 'add':
        add_card(app, args)
    elif args.command == 'edit':
        edit_card(app, args)
    elif args.command == 'delete':
        delete_card(app, args.id, args.force)
    else:
        print("Please specify a command. Use --help for more information.")

if __name__ == "__main__":
    main() 