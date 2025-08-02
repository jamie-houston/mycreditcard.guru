# Generated manually for UserCard recreation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cards', '0001_initial'),
    ]

    operations = [
        # Create the new UserCard model
        migrations.CreateModel(
            name='UserCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(blank=True, help_text='Optional nickname for this card', max_length=100)),
                ('opened_date', models.DateField(blank=True, help_text='Date when the card was opened/approved', null=True)),
                ('closed_date', models.DateField(blank=True, help_text='Date when the card was closed (if applicable)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notes', models.TextField(blank=True, help_text='Additional notes about this card')),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_ownerships', to='cards.creditcard')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_cards', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-opened_date', '-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='usercard',
            unique_together={('user', 'card')},
        ),
    ]