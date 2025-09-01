import stripe
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from servermanager.models import Profile

class Command(BaseCommand):
    help = 'Stripeの顧客IDを持たない既存のユーザーに対して、Stripe Customerを作成します。'

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.stdout.write("Stripe顧客IDの作成処理を開始します...")

        users_without_profiles = User.objects.filter(profile__isnull=True)
        if users_without_profiles.exists():
            self.stdout.write(f"{users_without_profiles.count()}人のユーザーにプロフィールが存在しません。作成します...")
            for user in users_without_profiles:
                Profile.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f"  -> プロフィールを作成しました: {user.username}"))

        profiles_without_customer_id = Profile.objects.filter(stripe_customer_id__isnull=True)
        if not profiles_without_customer_id.exists():
            self.stdout.write(self.style.SUCCESS("全てのユーザーは既にStripe顧客IDを持っています。処理を終了します。"))
            return

        self.stdout.write(f"{profiles_without_customer_id.count()}人のユーザーにStripe顧客IDが存在しません。作成します...")

        for profile in profiles_without_customer_id:
            user = profile.user
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.username,
                )
                profile.stripe_customer_id = customer.id
                profile.save()
                self.stdout.write(self.style.SUCCESS(f"  -> Stripe顧客を作成しました: {user.username} (ID: {customer.id})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> !! {user.username} の顧客作成に失敗しました: {e}"))
        
        self.stdout.write(self.style.SUCCESS("全ての処理が完了しました。"))
