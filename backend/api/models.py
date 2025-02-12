from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models

# Create your models here.


class AppUser(AbstractUser):
    public_key = models.TextField(unique=True, null=True)
    friends = models.ManyToManyField(
        "self", through="Friendship", symmetrical=False, related_name="friend_of"
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="appuser_set",
        related_query_name="user",
    )
    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
        related_name="appuser_set",
        related_query_name="user",
    )

    def __str__(self):
        return self.username


class ChatRoom(models.Model):
    user1 = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name="chatroom_user1"
    )
    user2 = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name="chatroom_user2"
    )
    user1_last_online = models.DateTimeField(null=True, blank=True)
    user2_last_online = models.DateTimeField(null=True, blank=True)

    numOfMessages = models.IntegerField(default=0)
    last_message_time = models.DateTimeField(null=True, blank=True)


class Message(models.Model):
    chat_room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name="messages"
    )
    senderUsername = models.CharField(max_length=200, null=True, blank=True)
    content = models.TextField(max_length=100000, null=True, blank=True)
    fileData = models.FileField(upload_to="uploads/", null=True, blank=True)
    isFile = models.BooleanField(default=False)
    fileName = models.TextField(null=True, blank=True)
    signature = models.TextField(max_length=100000, null=True, blank=True)
    iv = models.TextField(max_length=100000, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class Friendship(models.Model):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
    ]

    from_user = models.ForeignKey(
        AppUser, related_name="from_friend", on_delete=models.CASCADE
    )
    to_user = models.ForeignKey(
        AppUser, related_name="to_friend", on_delete=models.CASCADE
    )

    from_user_SK = models.TextField(unique=True, null=True)
    to_user_SK = models.TextField(unique=True, null=True)

    from_user_name = models.TextField(null=True, blank=True)
    to_user_name = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    class Meta:
        unique_together = ("from_user", "to_user", "status")
