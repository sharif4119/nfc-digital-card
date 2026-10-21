from django.db import migrations


def backfill(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    CardAllocation = apps.get_model("orders", "CardAllocation")
    for order in Order.objects.all().iterator():
        CardAllocation.objects.get_or_create(
            order_id=order.pk, position=1,
            defaults={"card_id": order.assigned_card_id},
        )


class Migration(migrations.Migration):
    dependencies = [("orders", "0003_order_business_order_type_order_business_profile_and_more")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
