"""Merge duplicate Travel subcategories created by inconsistent category seeds.

Two category seed files had drifted apart: data/input/system/spending_categories.json
(the authoritative seed, plural "hotels"/"airlines") and a redundant copy at
data/input/cards/spending_categories.json (singular "hotel"/"airline"). Both got
imported on deploy, and import_cards creates a category on demand by name, so both
forms ended up in the DB — making "Hotels" and "Airlines" appear twice in the
Average Monthly Spending UI. The redundant copy has since been removed so there is
a single category seed.

Plural is canonical (it matches the authoritative seed and the slug convention used
by the other count-noun categories: groceries, drugstores, rental_cars). This
repoints every reference (reward categories, card credits, spending credits, and
user spending amounts) from the singular row onto the plural row, then deletes the
now-empty singular row. The seed/card JSON files were also reconciled to the plural
slugs so future imports don't recreate the duplicates.
"""

from django.db import migrations

# (duplicate_slug -> canonical_slug)
MERGES = [
    ('hotel', 'hotels'),
    ('airline', 'airlines'),
]


def merge_categories(apps, schema_editor):
    SpendingCategory = apps.get_model('cards', 'SpendingCategory')
    RewardCategory = apps.get_model('cards', 'RewardCategory')
    SpendingCredit = apps.get_model('cards', 'SpendingCredit')
    CardCredit = apps.get_model('cards', 'CardCredit')
    SpendingAmount = apps.get_model('cards', 'SpendingAmount')

    for dup_slug, keep_slug in MERGES:
        dup = SpendingCategory.objects.filter(slug=dup_slug).first()
        keep = SpendingCategory.objects.filter(slug=keep_slug).first()
        if not dup or not keep or dup.pk == keep.pk:
            continue

        # RewardCategory: unique_together (card, category, start_date).
        for rc in RewardCategory.objects.filter(category=dup):
            clash = (RewardCategory.objects
                     .filter(card_id=rc.card_id, category=keep,
                             start_date=rc.start_date)
                     .exclude(pk=rc.pk).exists())
            if clash:
                rc.delete()
            else:
                rc.category = keep
                rc.save(update_fields=['category'])

        # No per-category uniqueness on these two; repoint in bulk.
        SpendingCredit.objects.filter(category=dup).update(category=keep)
        CardCredit.objects.filter(category=dup).update(category=keep)

        # SpendingAmount: unique_together (profile, category) -> sum on clash.
        for sa in SpendingAmount.objects.filter(category=dup):
            existing = (SpendingAmount.objects
                        .filter(profile_id=sa.profile_id, category=keep)
                        .first())
            if existing:
                existing.monthly_amount = ((existing.monthly_amount or 0)
                                           + (sa.monthly_amount or 0))
                existing.save(update_fields=['monthly_amount'])
                sa.delete()
            else:
                sa.category = keep
                sa.save(update_fields=['category'])

        dup.delete()


def noop(apps, schema_editor):
    # The merge can't be cleanly undone; leave the consolidated rows in place.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(merge_categories, noop),
    ]
