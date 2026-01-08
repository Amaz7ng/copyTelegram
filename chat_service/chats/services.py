from .models import Chat, ChatMember, Message

def get_or_create_direct_chat(user1, user2):
    """Находит или создает личный чат между двумя пользователями."""
    chat = Chat.objects.filter(type=Chat.DIRECT).filter(
        members__user=user1
    ).filter(
        members__user=user2
    ).first()

    if not chat:
        chat = Chat.objects.create(type=Chat.DIRECT)
        ChatMember.objects.create(chat=chat, user=user1, role=ChatMember.MEMBER)
        ChatMember.objects.create(chat=chat, user=user2, role=ChatMember.MEMBER)
    
    return chat

def repost_to_discussion(message, discussion_group):
    """Копирует сообщение из канала в связанную группу обсуждения."""
    return Message.objects.create(
        chat=discussion_group,
        sender=message.sender,
        text=message.text,
        file=message.file,
        file_type=message.file_type,
        reply_to=message 
    )