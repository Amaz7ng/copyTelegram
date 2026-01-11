import secrets
from django.utils import timezone

def send_otp_to_user(user):
    """Генерирует код, сохраняет его и 'отправляет' (пока в лог)."""
    otp = ''.join(secrets.choice('0123456789') for _ in range(6))
    user.otp_code = otp
    user.otp_created_at = timezone.now()
    user.save(update_fields=['otp_code', 'otp_created_at'])
    
    print(f"--- OTP SENT TO {user.username}: {otp} ---")
    return otp