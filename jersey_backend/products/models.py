import uuid
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    team = models.CharField(max_length=150, blank=True)
    season = models.CharField(max_length=50, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name="product_price_positive"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(discount_price__isnull=True) |
                    (
                        models.Q(discount_price__gt=0) &
                        models.Q(discount_price__lt=models.F("price"))
                    )
                ),
                name="product_discount_valid"
            ),
        ]

    def __str__(self):
        return self.name


class ProductVariant(models.Model):

    class Size(models.TextChoices):
        S = "S", "Small"
        M = "M", "Medium"
        L = "L", "Large"
        XL = "XL", "Extra Large"
        XXL = "XXL", "Double Extra Large"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )

    size = models.CharField(
        max_length=5,
        choices=Size.choices
    )

    stock = models.PositiveIntegerField(default=0)

    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True
    )

    class Meta:
        unique_together = ("product", "size")

    def __str__(self):
        return f"{self.product.name} - {self.size}"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = (
                f"JRS-{self.product_id}-{self.size}-"
                f"{uuid.uuid4().hex[:8].upper()}"
        )

        super().save(*args, **kwargs)