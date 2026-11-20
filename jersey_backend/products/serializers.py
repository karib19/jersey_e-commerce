from rest_framework import serializers
from .models import Category, Product, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "size",
            "stock",
            "sku",
        ]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "team",
            "season",
            "price",
            "discount_price",
            "image",
            "is_featured",
            "is_active",
            "variants",
            "created_at",
            "updated_at",
        ]

class AdminProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        source="category",
        write_only=True
    )

    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "category",
            "category_id",
            "team",
            "season",
            "price",
            "discount_price",
            "image",
            "is_featured",
            "is_active",
            "variants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "variants",
        ]

    def validate(self, attrs):
        price = attrs.get(
            "price",
            self.instance.price if self.instance else None
        )

        discount_price = attrs.get(
            "discount_price",
            self.instance.discount_price if self.instance else None
        )

        if price is not None and price <= 0:
            raise serializers.ValidationError({
                "price": "Price must be greater than zero."
            })

        if (
            discount_price is not None
            and price is not None
            and discount_price >= price
        ):
            raise serializers.ValidationError({
                "discount_price": "Discount price must be lower than regular price."
            })

        return attrs

class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

class AdminProductVariantSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "product",
            "product_name",
            "size",
            "stock",
            "sku",
        ]
        read_only_fields = ["id", "product", "product_name"]