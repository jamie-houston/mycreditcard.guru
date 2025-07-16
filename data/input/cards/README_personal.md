# Personal Card Import

The `personal.json` file allows you to import your owned credit cards with nicknames and opening dates.

## Format

```json
{
  "user_email": "your-actual-email@gmail.com",
  "owned_cards": [
    {
      "card_name": "Sapphire Preferred",
      "issuer": "Chase",
      "nickname": "Main Travel Card", 
      "opened_date": "2023-01-15"
    }
  ]
}
```

## Required Fields

- `user_email`: Must match an existing user account (sign up first)
- `card_name`: Must match exactly the card name in the database (without issuer prefix)
- `issuer`: Must match exactly the issuer name in the database

## Optional Fields

- `nickname`: Custom name for your card instance
- `opened_date`: Format YYYY-MM-DD

## Usage

1. Update `personal.json` with your email and cards
2. Run: `python admin.py import data/input/cards/personal.json`
3. Or: `python manage.py import_cards data/input/cards/personal.json`

## Notes

- You must have an existing user account (sign up via web interface first)
- Card names must exist in the database (import system cards first)
- This will replace all existing cards for the user
- You can have multiple instances of the same card with different nicknames