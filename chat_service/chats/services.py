from .models import Chat, ChatMember, Message
from django.db import transaction
from django.db.models import Count

def get_or_create_direct_chat(user1, user2):
    """
    Находит или создает личный чат между двумя пользователями.
    Проверяет, чтобы участников было строго двое.
    """
    # Если пытаемся создать чат с самим собой (избранное)
    if user1 == user2:
        chat = Chat.objects.filter(type=Chat.DIRECT, members__user=user1).annotate(
            u_count=Count('members')
        ).filter(u_count=1).first()
        
        if not chat:
            with transaction.atomic():
                chat = Chat.objects.create(type=Chat.DIRECT, title="Избранное")
                ChatMember.objects.create(chat=chat, user=user1, role=ChatMember.MEMBER)
        return chat

    # Поиск существующего чата между двумя разными юзерами
    chat = Chat.objects.filter(type=Chat.DIRECT).annotate(
        u_count=Count('members')
    ).filter(u_count=2).filter(
        members__user=user1
    ).filter(
        members__user=user2
    ).distinct().first()

    if not chat:
        with transaction.atomic():
            # Для Direct-чата title обычно пустой, берется из имени собеседника в сериализаторе
            chat = Chat.objects.create(type=Chat.DIRECT)
            ChatMember.objects.create(chat=chat, user=user1, role=ChatMember.MEMBER)
            ChatMember.objects.create(chat=chat, user=user2, role=ChatMember.MEMBER)
    
    return chat

def repost_to_discussion(message, discussion_group):
    """Копирует сообщение из канала в связанную группу обсуждения."""
    # Важно: поле file в Django — это путь. Копируя его так, 
    # мы ссылаемся на тот же файл в хранилище без дублирования байтов.
    return Message.objects.create(
        chat=discussion_group,
        sender=message.sender,
        text=message.text,
        file=message.file,
        file_type=message.file_type,
        reply_to=message 
    )