"""Backfill a primary ProfileEntity for every existing profile and point
every existing UserCard at it.

Phase K (multi-player households): UserCard.owner=NULL now means "the
profile's primary entity" going forward, but pre-existing rows have no
owner set at all and no ProfileEntity exists yet. This creates one primary
entity per UserSpendingProfile (auth and session-key both, for uniformity)
and assigns it to every UserCard the corresponding user already holds.
Session-key profiles have no UserCards of their own (anonymous ownership
lives in localStorage), so this is a no-op for them beyond creating the row.

Reverse is a no-op — there's nothing to cleanly undo (rows created after
this point may already reference these entities).
"""

from django.db import migrations


def backfill(apps, schema_editor):
    UserSpendingProfile = apps.get_model('cards', 'UserSpendingProfile')
    ProfileEntity = apps.get_model('cards', 'ProfileEntity')
    UserCard = apps.get_model('cards', 'UserCard')

    # Every user who owns at least one UserCard needs a profile to hang the
    # primary entity off of, even if they never separately created one.
    owning_user_ids = (UserCard.objects.values_list('user_id', flat=True)
                       .distinct())
    for user_id in owning_user_ids:
        UserSpendingProfile.objects.get_or_create(user_id=user_id)

    for profile in UserSpendingProfile.objects.all():
        if profile.user:
            name = profile.user.first_name or profile.user.username or 'Player 1'
        else:
            name = 'Player 1'
        entity, _ = ProfileEntity.objects.get_or_create(
            profile=profile, is_primary=True,
            defaults={'name': name, 'kind': 'personal'})
        if profile.user:
            UserCard.objects.filter(
                user=profile.user, owner__isnull=True
            ).update(owner=entity)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0007_profileentity_usercard_owner'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
