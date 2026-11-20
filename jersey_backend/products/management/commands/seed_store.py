from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from products.models import Category, Product, ProductVariant


PRODUCTS = [
    {
        "name": "Argentina 2026 Home Jersey",
        "team": "Argentina",
        "season": "2026",
        "price": "3200.00",
        "discount_price": "2750.00",
        "image": "images7.jpg",
        "featured": True,
        "sizes": {"M": 8, "L": 12, "XL": 5},
    },
    {
        "name": "Brazil 2026 Away Jersey",
        "team": "Brazil",
        "season": "2026",
        "price": "2900.00",
        "image": "image9.webp",
        "sizes": {"S": 6, "M": 9, "L": 5},
    },
    {
        "name": "Real Madrid Home Jersey",
        "team": "Real Madrid",
        "season": "2025/26",
        "price": "3500.00",
        "image": "image2.webp",
        "featured": True,
        "sizes": {"M": 11, "L": 7, "XL": 4},
    },
    {
        "name": "FC Barcelona Home Jersey",
        "team": "FC Barcelona",
        "season": "2025/26",
        "price": "3300.00",
        "discount_price": "2950.00",
        "image": "image1.jpg",
        "featured": True,
        "sizes": {"S": 3, "M": 10, "L": 8},
    },
    {
        "name": "AC Milan Home Jersey",
        "team": "AC Milan",
        "season": "2025/26",
        "price": "2800.00",
        "image": "image5.jpg",
        "sizes": {"M": 7, "L": 6, "XXL": 2},
    },
    {
        "name": "Manchester City Home Jersey",
        "team": "Manchester City",
        "season": "2025/26",
        "price": "3100.00",
        "image": "image6.jpg",
        "sizes": {"S": 5, "M": 8, "XL": 3},
    },
    {
        "name": "Manchester United Home Jersey",
        "team": "Manchester United",
        "season": "2021/22",
        "price": "3000.00",
        "image": "image4.jpg",
        "featured": True,
        "sizes": {"M": 4, "L": 7, "XL": 5},
    },
    {
        "name": "Bayern Munich Home Jersey",
        "team": "Bayern Munich",
        "season": "2025/26",
        "price": "3000.00",
        "image": "image3.jpg",
        "sizes": {"S": 4, "L": 9, "XL": 6},
    },
    {
        "name": "Inter Milan Home Jersey",
        "team": "Inter Milan",
        "season": "2023/24",
        "price": "2900.00",
        "image": "image10.webp",
        "sizes": {"M": 5, "L": 8},
    },
    {
        "name": "Chelsea Home Jersey",
        "team": "Chelsea",
        "season": "2021/22",
        "price": "2800.00",
        "image": "image17.jpg",
        "sizes": {"M": 4, "L": 6},
    },
    {
        "name": "Adidas Training Shorts",
        "team": "Training wear",
        "price": "1200.00",
        "image": "image12.jpg",
        "sizes": {"M": 8, "L": 6},
    },
    {
        "name": "Classic White Training Shorts",
        "team": "Training wear",
        "price": "1250.00",
        "image": "image13.jpg",
        "sizes": {"M": 8, "L": 6},
    },
    {
        "name": "Sky Blue Training Shorts",
        "team": "Training wear",
        "price": "1400.00",
        "image": "image14.jpg",
        "sizes": {"M": 8, "L": 6},
    },
    {
        "name": "Brazil Training Shorts",
        "team": "Training wear",
        "price": "1450.00",
        "image": "image15.jpg",
        "sizes": {"M": 8, "L": 6},
    },
    {
        "name": "Track Training Pants",
        "team": "Training wear",
        "price": "1850.00",
        "image": "image16.jpg",
        "sizes": {"M": 8, "L": 6},
    },
]


class Command(BaseCommand):
    help = "Create/update the portfolio demo catalog and size stock from local product photos."

    @transaction.atomic
    def handle(self, *args, **options):
        image_dir = Path(__file__).resolve().parents[3] / "media" / "products"
        missing_images = sorted({item["image"] for item in PRODUCTS} - {path.name for path in image_dir.iterdir()})
        if missing_images:
            raise CommandError(f"Missing product images in {image_dir}: {', '.join(missing_images)}")

        football, _ = Category.objects.update_or_create(
            slug="club-jerseys",
            defaults={"name": "Club jerseys", "description": "Football club and national team jerseys.", "is_active": True},
        )
        training, _ = Category.objects.update_or_create(
            slug="training-wear",
            defaults={"name": "Training wear", "description": "Shorts and training essentials.", "is_active": True},
        )

        created_count = updated_count = variants_created = 0
        for data in PRODUCTS:
            category = training if data["team"] == "Training wear" else football
            slug = slugify(data["name"])
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": category,
                    "name": data["name"],
                    "description": f"{data['team']} {category.name.lower()}, selected for supporters and made for match day.",
                    "team": data["team"],
                    "season": data.get("season", ""),
                    "price": data["price"],
                    "discount_price": data.get("discount_price"),
                    "image": f"products/{data['image']}",
                    "is_featured": data.get("featured", False),
                    "is_active": True,
                },
            )
            created_count += int(created)
            updated_count += int(not created)

            for size, stock in data["sizes"].items():
                _, variant_created = ProductVariant.objects.get_or_create(
                    product=product,
                    size=size,
                    defaults={"stock": stock},
                )
                variants_created += int(variant_created)

        self.stdout.write(self.style.SUCCESS(
            f"Store catalog ready: {created_count} products created, {updated_count} updated, "
            f"{variants_created} size variants created. Existing variant stock was preserved."
        ))
