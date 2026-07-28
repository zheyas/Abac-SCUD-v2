from rest_framework import serializers

from .models import AccessEvent, AccessGroup, AccessUser, Building, Policy


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = [
            "id",
            "name",
            "color_hex",
            "x",
            "y",
            "w",
            "h",
            "depth",
            "is_accessible_to_all",
            "open_days",
            "open_time",
            "close_time",
            "is_24_hours",
        ]


class AccessGroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    access_count = serializers.IntegerField(read_only=True)
    building_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = AccessGroup
        fields = ["id", "name", "description", "member_count", "access_count", "building_ids"]


class AccessUserSerializer(serializers.ModelSerializer):
    group_id = serializers.PrimaryKeyRelatedField(source="group", queryset=AccessGroup.objects.all())
    group_name = serializers.CharField(source="group.name", read_only=True)
    role_id = serializers.IntegerField(source="group_id", read_only=True)
    role_name = serializers.CharField(source="group.name", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    personal_building_ids = serializers.PrimaryKeyRelatedField(
        source="personal_buildings",
        queryset=Building.objects.filter(is_accessible_to_all=False),
        many=True,
        required=False,
    )

    class Meta:
        model = AccessUser
        fields = [
            "id",
            "username",
            "password",
            "group_id",
            "group_name",
            "role_id",
            "role_name",
            "is_active",
            "shift_status",
            "shift_auto",
            "shift_days",
            "shift_start",
            "shift_end",
            "personal_building_ids",
        ]

    def validate_password(self, value):
        if value and len(value) < 6:
            raise serializers.ValidationError("Пароль должен быть не короче 6 символов")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        personal_buildings = validated_data.pop("personal_buildings", [])
        if not password:
            raise serializers.ValidationError({"password": "Укажите пароль"})
        user = AccessUser(**validated_data)
        user.set_password(password)
        user.save()
        user.personal_buildings.set(personal_buildings)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        personal_buildings = validated_data.pop("personal_buildings", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        if personal_buildings is not None:
            instance.personal_buildings.set(personal_buildings)
        return instance


class PolicySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    building_name = serializers.CharField(source="building.name", read_only=True)

    class Meta:
        model = Policy
        fields = [
            "id",
            "name",
            "group",
            "group_name",
            "user",
            "user_name",
            "building",
            "building_name",
            "days_allowed",
            "time_start",
            "time_end",
            "requires_shift_active",
            "effect",
            "is_active",
        ]


class AccessEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    building_name = serializers.CharField(source="building.name", read_only=True)

    class Meta:
        model = AccessEvent
        fields = [
            "id",
            "user",
            "username",
            "building",
            "building_name",
            "attempted_at",
            "context_time",
            "result",
            "reason",
            "rule_name",
            "source",
        ]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class AccessStatusRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    timestamp = serializers.CharField(required=False, allow_blank=True)


class EntryAttemptSerializer(serializers.Serializer):
    building_id = serializers.IntegerField()
    timestamp = serializers.CharField(required=False, allow_blank=True)
    user_id = serializers.IntegerField(required=False)
