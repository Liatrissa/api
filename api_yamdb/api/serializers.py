from django.conf import settings
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.relations import SlugRelatedField
from rest_framework.validators import UniqueTogetherValidator

from reviews.models import Category, Comment, Genre, Review, Title
from users.models import User, CHOICE_ROLES
from users.utils import get_unique_confirmation_code
from users.utils import username_validate, email_validate


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        exclude = ('id', )
        model = Category
        lookup_field = 'slug'


class GenreSerializer(serializers.ModelSerializer):

    class Meta:
        exclude = ('id', )
        model = Genre
        lookup_field = 'slug'


class TitleReadSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    genre = GenreSerializer(
        read_only=True,
        many=True
    )
    rating = serializers.IntegerField(read_only=True)

    class Meta:
        fields = '__all__'
        model = Title


class TitleWriteSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field='slug'
    )
    genre = serializers.SlugRelatedField(
        queryset=Genre.objects.all(),
        slug_field='slug',
        many=True
    )

    class Meta:
        fields = '__all__'
        model = Title


class ReviewSerializer(serializers.ModelSerializer):
    author = SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    title = SlugRelatedField(
        slug_field='name',
        read_only=True
    )

    def validate(self, data):
        request = self.context['request']
        author = request.user
        title_id = self.context['view'].kwargs.get('title_id')
        title = get_object_or_404(Title, pk=title_id)
        # проверяем, хочет ли юзер отправить запрос на создание Отзыва
        if request.method == 'POST':
            # проверяем есть ли отзыв у этого произведения
            # и принадлежит ли он автору запроса
            if Review.objects.filter(title=title, author=author).exists():
                raise serializers.ValidationError(
                    'Нельзя добавить больше одного отзыва'
                )
        return data

    class Meta:
        fields = '__all__'
        model = Review


class CommentSerializer(serializers.ModelSerializer):
    author = SlugRelatedField(
        read_only=True, slug_field='username'
    )
    reviews = SlugRelatedField(
        slug_field='text', read_only=True
    )

    class Meta:
        fields = '__all__'
        model = Comment


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор модели User для обычных пользователей - не админов"""

    email = serializers.EmailField(max_length=254)
    username = serializers.CharField(max_length=150)

    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'first_name',
            'last_name',
            'bio',
            'role'
        ]

        validators = (
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=['username', 'email']
            ),
        )

    def create(self, validated_data):
        confirm_code = str(get_unique_confirmation_code)
        return User.objects.create(
            **validated_data,
            confirmation_code=confirm_code
        )


    def validate(self, data):
        username_validate(str(data.get('username')))
        email_validate(str(data.get('email')))
        return data


class MeSerializer(serializers.ModelSerializer):
    """Сериализатор модели User для редактирования профайла"""

    email = serializers.EmailField(max_length=254)
    username = serializers.CharField(max_length=150)
    role = serializers.CharField(max_length=15, read_only=True)

    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'first_name',
            'last_name',
            'bio',
            'role'
        ]

        validators = (
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=['username', 'email']
            ),
        )

    def validate(self, data):
        username_validate(str(data.get('username')))
        email_validate(str(data.get('email')))
        return data


class AdminOrSuperAdminUserSerializer(serializers.ModelSerializer):
    """Сериализатор модели User для пользователей админ и суперадмин.
    Этим пользователям доступно редактирование роли"""

    email = serializers.EmailField(max_length=254)
    username = serializers.CharField(max_length=150)
    role = serializers.CharField(max_length=15, default='user')

    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'first_name',
            'last_name',
            'bio',
            'role',
        ]

        validators = (
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=['username', 'email']
            ),
        )

    def create(self, validated_data):
        confirm_code = str(get_unique_confirmation_code)
        return User.objects.create(
            **validated_data,
            confirmation_code=confirm_code
        )

    def validate(self, data):
        username_validate(str(data.get('username')))
        email_validate(str(data.get('email')))
        role = str(data.get('role'))
        if  (any(role in i for i in CHOICE_ROLES)):
                raise serializers.ValidationError(
                    'Задана не существующая роль'
                )
        return data


class SignUpSerializer(serializers.ModelSerializer):
    """Сериализатор запроса авторизации"""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)

    class Meta:
        model = User
        fields = [
            'username',
            'email'
        ]

    class Meta:
        model = User
        fields = [
            'username',
            'email',
        ]

    def validate(self, data):
        username_validate(str(data.get('username')))
        email_validate(str(data.get('username')))
        return data


class TokenSerializer(serializers.ModelSerializer):
    """Сериализатор получения токена по коду подтверждения"""
    username = serializers.CharField(
        max_length=150)

    confirmation_code = serializers.CharField(
        max_length=settings.MAX_CODE_LENGTH)

    class Meta:
        model = User
        fields = [
            'username',
            'confirmation_code',
        ]

    def validate(self, data):
        username = str(data.get('username'))
        confirmation_code = data.get('confirmation_code')
        if confirmation_code is None:
            raise serializers.ValidationError(
                'Код подтверждения не может быть пустым'
                )
        username_validate(username)
        return data
