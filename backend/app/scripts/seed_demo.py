"""
╔══════════════════════════════════════════════════════════════════╗
║         DineOS — Demo Seed Script (backend/app/scripts/)         ║
║                                                                  ║
║  Usage:                                                          ║
║    # Run from backend/ directory:                                ║
║    python -m app.scripts.seed_demo              # idempotent     ║
║    python -m app.scripts.seed_demo --reset      # wipe & reseed  ║
║                                                                  ║
║  Hits the DB directly (no HTTP) via existing SQLAlchemy models.  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import sys
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

# ── SQLAlchemy setup ──────────────────────────────────────────────────────────
from sqlalchemy import delete, select, text

# ── App imports ───────────────────────────────────────────────────────────────
from app.core.db import AsyncSessionLocal
from app.core.security import hash_password

# ── Models ────────────────────────────────────────────────────────────────────
from app.modules.auth.models import Role, User
from app.modules.billing.models import (
    GSTTransaction,
    GSTType,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.crm.models import Customer, Feedback, LoyaltyTransaction
from app.modules.inventory.models import Ingredient, Recipe, RecipeIngredient, StockLedger, Unit
from app.modules.menu.models import (
    ItemAddon,
    ItemVariant,
    MenuCategory,
    MenuItem,
    MenuItemBranchPrice,
)
from app.modules.operations.models import DiningTable, Floor, TableSection
from app.modules.orders.models import (
    KotTicket,
    Order,
    OrderAddon,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    OrderType,
)
from app.modules.subscriptions.models import (
    PlanInterval,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.modules.tenancy.models import Branch, Restaurant, RestaurantSettings

# ─────────────────────────────────────────────────────────────────────────────
# Seed constants
# ─────────────────────────────────────────────────────────────────────────────
PLAIN_PASSWORD = "Password123!"
DEMO_MARKER = "SEED_DEMO_v1"   # stored as restaurant.fssai_number so we can detect existing seed


# ─────────────────────────────────────────────────────────────────────────────
# Helper: generate realistic order numbers
# ─────────────────────────────────────────────────────────────────────────────
def _order_number(tag: str) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    return f"ORD-{today}-{tag.upper()}"


def _invoice_number(tag: str) -> str:
    today = datetime.utcnow().strftime("%Y%m")
    return f"INV-{today}-{tag.upper()}"


# ─────────────────────────────────────────────────────────────────────────────
# RESET  — delete everything from a previous demo run
# ─────────────────────────────────────────────────────────────────────────────
async def _reset(db):
    print("[RESET] Wiping previous demo data...")
    # Find demo restaurant by fssai_number marker
    result = await db.execute(
        select(Restaurant).where(Restaurant.fssai_number == DEMO_MARKER)
    )
    rest = result.scalar_one_or_none()
    if rest:
        rest_id = rest.id
        from app.modules.billing.models import GSTTransaction, Invoice, InvoiceItem, Payment
        from app.modules.crm.models import Coupon, Customer, Feedback, LoyaltyTransaction, MembershipTier, Offer
        from app.modules.inventory.models import (
            Ingredient,
            PurchaseOrder,
            PurchaseOrderItem,
            Recipe,
            RecipeIngredient,
            StockLedger,
            Unit,
            Vendor,
        )
        from app.modules.menu.models import ItemVariant, MenuCategory, MenuItem
        from app.modules.operations.models import DiningTable, Floor, TableSection, Tip, TipAllocation
        from app.modules.orders.models import KotTicket, Order, OrderAddon, OrderItem, OrderStatusHistory

        await db.execute(delete(StockLedger).where(StockLedger.restaurant_id == rest_id))
        await db.execute(delete(Subscription).where(Subscription.restaurant_id == rest_id))
        await db.execute(delete(GSTTransaction).where(GSTTransaction.restaurant_id == rest_id))
        await db.execute(delete(Payment).where(Payment.invoice_id.in_(select(Invoice.id).where(Invoice.restaurant_id == rest_id))))
        await db.execute(delete(InvoiceItem).where(InvoiceItem.invoice_id.in_(select(Invoice.id).where(Invoice.restaurant_id == rest_id))))
        await db.execute(delete(Invoice).where(Invoice.restaurant_id == rest_id))
        await db.execute(delete(KotTicket).where(KotTicket.restaurant_id == rest_id))
        await db.execute(delete(OrderStatusHistory).where(OrderStatusHistory.order_id.in_(select(Order.id).where(Order.restaurant_id == rest_id))))
        await db.execute(delete(OrderAddon).where(OrderAddon.order_item_id.in_(select(OrderItem.id).where(OrderItem.order_id.in_(select(Order.id).where(Order.restaurant_id == rest_id))))))
        await db.execute(delete(OrderItem).where(OrderItem.order_id.in_(select(Order.id).where(Order.restaurant_id == rest_id))))
        await db.execute(delete(Order).where(Order.restaurant_id == rest_id))
        await db.execute(delete(LoyaltyTransaction).where(LoyaltyTransaction.restaurant_id == rest_id))
        await db.execute(delete(Feedback).where(Feedback.restaurant_id == rest_id))
        await db.execute(delete(Coupon).where(Coupon.restaurant_id == rest_id))
        await db.execute(delete(Offer).where(Offer.restaurant_id == rest_id))
        await db.execute(delete(MembershipTier).where(MembershipTier.restaurant_id == rest_id))
        await db.execute(delete(Customer).where(Customer.restaurant_id == rest_id))
        await db.execute(delete(RecipeIngredient).where(RecipeIngredient.ingredient_id.in_(select(Ingredient.id).where(Ingredient.restaurant_id == rest_id))))
        await db.execute(delete(Recipe).where(Recipe.restaurant_id == rest_id))
        await db.execute(delete(Ingredient).where(Ingredient.restaurant_id == rest_id))
        await db.execute(delete(Unit).where(Unit.restaurant_id == rest_id))
        await db.execute(delete(PurchaseOrderItem).where(PurchaseOrderItem.order_id.in_(select(PurchaseOrder.id).where(PurchaseOrder.restaurant_id == rest_id))))
        await db.execute(delete(PurchaseOrder).where(PurchaseOrder.restaurant_id == rest_id))
        await db.execute(delete(Vendor).where(Vendor.restaurant_id == rest_id))
        await db.execute(delete(ItemVariant).where(ItemVariant.item_id.in_(select(MenuItem.id).where(MenuItem.restaurant_id == rest_id))))
        from app.modules.menu.models import ItemAddon
        await db.execute(delete(ItemAddon).where(ItemAddon.item_id.in_(select(MenuItem.id).where(MenuItem.restaurant_id == rest_id))))
        await db.execute(delete(MenuItem).where(MenuItem.restaurant_id == rest_id))
        await db.execute(delete(MenuCategory).where(MenuCategory.restaurant_id == rest_id))
        await db.execute(delete(TipAllocation).where(TipAllocation.tip_id.in_(select(Tip.id).where(Tip.restaurant_id == rest_id))))
        await db.execute(delete(Tip).where(Tip.restaurant_id == rest_id))
        await db.execute(delete(DiningTable).where(DiningTable.restaurant_id == rest_id))
        await db.execute(delete(TableSection).where(TableSection.floor_id.in_(select(Floor.id).where(Floor.restaurant_id == rest_id))))
        await db.execute(delete(Floor).where(Floor.restaurant_id == rest_id))
        await db.execute(delete(Branch).where(Branch.restaurant_id == rest_id))
        await db.execute(delete(RestaurantSettings).where(RestaurantSettings.restaurant_id == rest_id))

        await db.execute(delete(Restaurant).where(Restaurant.id == rest_id))
        await db.execute(delete(SubscriptionPlan).where(SubscriptionPlan.slug == "pro-monthly-demo"))

    # Delete demo users by email pattern
    await db.execute(
        delete(User).where(User.email.like("%@spiceroute.demo"))
    )
    # Delete super_admin demo user
    await db.execute(
        delete(User).where(User.email == "superadmin@dineos.demo")
    )
    await db.commit()
    print("[OK] Reset complete.\n")


# ─────────────────────────────────────────────────────────────────────────────
# IDEMPOTENCY CHECK — skip if already seeded
# ─────────────────────────────────────────────────────────────────────────────
async def _already_seeded(db) -> bool:
    result = await db.execute(
        select(Restaurant).where(Restaurant.fssai_number == DEMO_MARKER)
    )
    return result.scalar_one_or_none() is not None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SEED
# ─────────────────────────────────────────────────────────────────────────────
async def seed(reset: bool = False):
    # Ensure missing tables are created (like subscriptions)
    from app.core.db import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure PARTIALLY_PAID exists in the PG paymentstatus enum type
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        res = await conn.execute(text("""
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON t.oid = e.enumtypid
            WHERE t.typname = 'paymentstatus' AND e.enumlabel = 'PARTIALLY_PAID'
        """))
        exists = res.scalar()
        if not exists:
            await conn.execute(text("ALTER TYPE paymentstatus ADD VALUE 'PARTIALLY_PAID'"))

    async with AsyncSessionLocal() as db:

        # ── Reset? ────────────────────────────────────────────────────────────
        if reset:
            await _reset(db)
        elif await _already_seeded(db):
            print("[INFO] Demo data already exists. Run with --reset to wipe & reseed.")
            # Still print summary from existing data
            await _print_summary(db)
            return

        print("[*] Seeding DineOS demo data...\n")

        # ══════════════════════════════════════════════════════════════════════
        # 1. TENANCY
        # ══════════════════════════════════════════════════════════════════════
        print("── [1/10] Tenancy …")

        restaurant = Restaurant(
            name="Spice Route",
            slug="spice-route-demo",
            email="info@spiceroute.demo",
            phone="+918012345678",
            address="12, MG Road, Connaught Place",
            city="New Delhi",
            state="Delhi",
            country="India",
            gstin="07AABCS1429B1Z0",   # realistic Delhi GSTIN format
            fssai_number=DEMO_MARKER,   # used as idempotency marker
            is_active=True,
        )
        db.add(restaurant)
        await db.flush()

        settings_obj = RestaurantSettings(
            restaurant_id=restaurant.id,
            currency="INR",
            timezone="Asia/Kolkata",
            tax_inclusive=False,
            default_gst_rate=5.0,
            cgst_rate=2.5,
            sgst_rate=2.5,
            igst_rate=0.0,
            tip_enabled=True,
            invoice_prefix="SR",
        )
        db.add(settings_obj)

        branch_main = Branch(
            restaurant_id=restaurant.id,
            name="Main Street",
            address="12, MG Road, Connaught Place, New Delhi",
            phone="+911123456789",
            is_active=True,
            is_default=True,
        )
        branch_mall = Branch(
            restaurant_id=restaurant.id,
            name="Mall Road",
            address="DLF Mall, Saket, New Delhi",
            phone="+911198765432",
            is_active=True,
            is_default=False,
        )
        db.add_all([branch_main, branch_mall])
        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 2. AUTH / RBAC
        # ══════════════════════════════════════════════════════════════════════
        print("── [2/10] Auth / RBAC …")

        # Fetch or create roles
        role_map: dict[str, Role] = {}
        for role_name in ["owner", "manager", "cashier", "kitchen", "super_admin"]:
            res = await db.execute(select(Role).where(Role.name == role_name))
            role_obj = res.scalar_one_or_none()
            if not role_obj:
                role_obj = Role(name=role_name, description=f"{role_name} role")
                db.add(role_obj)
                await db.flush()
            role_map[role_name] = role_obj

        # Also handle "waiter" role (may not exist in seed)
        res = await db.execute(select(Role).where(Role.name == "waiter"))
        waiter_role = res.scalar_one_or_none()
        if not waiter_role:
            waiter_role = Role(name="waiter", description="waiter role")
            db.add(waiter_role)
            await db.flush()
        role_map["waiter"] = waiter_role

        hashed_pw = hash_password(PLAIN_PASSWORD)

        def make_user(email, full_name, role_name, restaurant_id=None, branch_id=None):
            u = User(
                email=email,
                hashed_password=hashed_pw,
                full_name=full_name,
                phone=f"+919{str(uuid.uuid4().int)[:9]}",
                is_active=True,
                is_verified=True,
                phone_verified=True,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
            )
            u.roles.append(role_map[role_name])
            return u

        user_owner = make_user("owner@spiceroute.demo", "Rajesh Kumar", "owner", restaurant.id)
        user_manager = make_user("manager@spiceroute.demo", "Priya Sharma", "manager", restaurant.id, branch_main.id)
        user_cashier = make_user("cashier@spiceroute.demo", "Amit Verma", "cashier", restaurant.id, branch_main.id)
        user_waiter = make_user("waiter@spiceroute.demo", "Suresh Yadav", "waiter", restaurant.id, branch_main.id)
        user_kitchen = make_user("kitchen@spiceroute.demo", "Ramesh Singh", "kitchen", restaurant.id, branch_main.id)
        user_super = make_user("superadmin@dineos.demo", "DineOS Admin", "super_admin", None)

        db.add_all([user_owner, user_manager, user_cashier, user_waiter, user_kitchen, user_super])
        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 3. OPERATIONS — floors, sections, tables
        # ══════════════════════════════════════════════════════════════════════
        print("── [3/10] Operations …")

        all_tables: list[DiningTable] = []

        for branch, floor_name, section_names in [
            (branch_main, "Ground Floor", ["Garden Section", "Main Hall"]),
            (branch_mall, "First Floor", ["Window Side", "Central Area"]),
        ]:
            floor = Floor(
                restaurant_id=restaurant.id,
                branch_id=branch.id,
                name=floor_name,
                sort_order=1,
                is_active=True,
            )
            db.add(floor)
            await db.flush()

            for sec_name in section_names:
                section = TableSection(
                    floor_id=floor.id,
                    name=sec_name,
                    is_active=True,
                )
                db.add(section)
                await db.flush()

                # 4 tables in first section, 5 in the second
                table_count = 4 if sec_name == section_names[0] else 5
                capacities = [2, 4, 4, 6, 8]
                for t_idx in range(table_count):
                    t = DiningTable(
                        restaurant_id=restaurant.id,
                        section_id=section.id,
                        table_number=f"{sec_name[:1]}{t_idx + 1}",
                        capacity=capacities[t_idx % len(capacities)],
                        is_occupied=False,
                        is_active=True,
                    )
                    db.add(t)
                    all_tables.append(t)

        await db.flush()

        table_main = all_tables[0]   # first table in Main Street branch

        # ══════════════════════════════════════════════════════════════════════
        # 4. MENU — categories, items, variants, addons, branch price override
        # ══════════════════════════════════════════════════════════════════════
        print("── [4/10] Menu …")

        # ── Categories ───────────────────────────────────────────────────────
        cat_starters = MenuCategory(restaurant_id=restaurant.id, name="Starters",
                                    description="Appetizers and light bites", sort_order=1)
        cat_mains = MenuCategory(restaurant_id=restaurant.id, name="Main Course",
                                 description="Hearty main dishes", sort_order=2)
        cat_beverages = MenuCategory(restaurant_id=restaurant.id, name="Beverages",
                                     description="Hot and cold drinks", sort_order=3)
        cat_desserts = MenuCategory(restaurant_id=restaurant.id, name="Desserts",
                                    description="Sweet endings", sort_order=4)
        db.add_all([cat_starters, cat_mains, cat_beverages, cat_desserts])
        await db.flush()

        # ── Helper: build a MenuItem ──────────────────────────────────────────
        def menu_item(cat, name, price, gst, veg=True, desc="", hsn="996331"):
            return MenuItem(
                restaurant_id=restaurant.id,
                category_id=cat.id,
                name=name,
                description=desc,
                base_price=Decimal(str(price)),
                is_veg=veg,
                is_available=True,
                gst_rate=Decimal(str(gst)),
                hsn_code=hsn,
            )

        # ── Starters (5% GST) ─────────────────────────────────────────────────
        item_paneer_tikka = menu_item(cat_starters, "Paneer Tikka", 220, 5,
                                      desc="Grilled cottage cheese with spices")
        item_veg_platter = menu_item(cat_starters, "Veg Kebab Platter", 280, 5,
                                     desc="Assorted vegetable kebabs")
        item_chicken_tikka = menu_item(cat_starters, "Chicken Tikka", 350, 5, veg=False,
                                       desc="Marinated grilled chicken")
        item_samosa = menu_item(cat_starters, "Crispy Samosa (2 pcs)", 80, 5,
                                desc="Golden fried samosas with mint chutney")

        # ── Main Course (12% GST for full meals) ──────────────────────────────
        item_dal_makhani = menu_item(cat_mains, "Dal Makhani", 260, 12,
                                     desc="Slow-cooked black lentils in butter gravy")
        item_butter_chicken = menu_item(cat_mains, "Butter Chicken", 380, 12, veg=False,
                                        desc="Classic creamy tomato chicken curry")
        item_biryani = menu_item(cat_mains, "Hyderabadi Veg Biryani", 310, 12,
                                 desc="Fragrant basmati rice with vegetables & saffron")
        item_paneer_kadai = menu_item(cat_mains, "Paneer Kadai", 300, 12,
                                      desc="Cottage cheese in spiced onion-tomato gravy")

        # ── Beverages (5% GST) ────────────────────────────────────────────────
        item_lassi = menu_item(cat_beverages, "Sweet Lassi", 90, 5,
                               desc="Chilled yogurt drink")
        item_masala_chai = menu_item(cat_beverages, "Masala Chai", 50, 5,
                                     desc="Spiced milk tea")
        item_cold_coffee = menu_item(cat_beverages, "Cold Coffee", 140, 5,
                                     desc="Iced blended coffee")

        # ── Desserts (5% GST) ─────────────────────────────────────────────────
        item_gulab_jamun = menu_item(cat_desserts, "Gulab Jamun (2 pcs)", 110, 5,
                                     desc="Soft milk dumplings in sugar syrup")
        item_kheer = menu_item(cat_desserts, "Rice Kheer", 130, 5,
                               desc="Creamy rice pudding with cardamom & nuts")
        item_rasgulla = menu_item(cat_desserts, "Rasgulla (3 pcs)", 100, 5,
                                  desc="Spongy cottage cheese balls in light syrup")

        db.add_all([
            item_paneer_tikka, item_veg_platter, item_chicken_tikka, item_samosa,
            item_dal_makhani, item_butter_chicken, item_biryani, item_paneer_kadai,
            item_lassi, item_masala_chai, item_cold_coffee,
            item_gulab_jamun, item_kheer, item_rasgulla,
        ])
        await db.flush()

        # ── Variants: half / full for Dal Makhani and Paneer Tikka ───────────
        dal_half = ItemVariant(item_id=item_dal_makhani.id, name="Half", price=Decimal("180.00"))
        dal_full = ItemVariant(item_id=item_dal_makhani.id, name="Full", price=Decimal("260.00"))
        tikka_half = ItemVariant(item_id=item_paneer_tikka.id, name="Half Plate", price=Decimal("150.00"))
        tikka_full = ItemVariant(item_id=item_paneer_tikka.id, name="Full Plate", price=Decimal("220.00"))
        db.add_all([dal_half, dal_full, tikka_half, tikka_full])

        # ── Addons: toppings for Biryani ──────────────────────────────────────
        addon_raita = ItemAddon(item_id=item_biryani.id, name="Raita (add-on)", price=Decimal("50.00"))
        addon_papad = ItemAddon(item_id=item_biryani.id, name="Papad", price=Decimal("20.00"))
        addon_salan = ItemAddon(item_id=item_biryani.id, name="Mirchi ka Salan", price=Decimal("60.00"))
        db.add_all([addon_raita, addon_papad, addon_salan])

        await db.flush()

        # ── Branch price override: Butter Chicken costs ₹10 more at Mall Road ─
        branch_price_override = MenuItemBranchPrice(
            menu_item_id=item_butter_chicken.id,
            branch_id=branch_mall.id,
            price=Decimal("390.00"),
        )
        db.add(branch_price_override)
        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 5. INVENTORY — units, ingredients, recipes
        # ══════════════════════════════════════════════════════════════════════
        print("── [5/10] Inventory …")

        # ── Units (global, upsert by name) ────────────────────────────────────
        async def get_or_create_unit(name, abbr):
            r = await db.execute(select(Unit).where(Unit.name == name))
            u = r.scalar_one_or_none()
            if not u:
                u = Unit(name=name, abbreviation=abbr, restaurant_id=restaurant.id)
                db.add(u)
                await db.flush()
            return u

        unit_kg = await get_or_create_unit("Kilogram", "kg")
        unit_g = await get_or_create_unit("Gram", "g")
        unit_litre = await get_or_create_unit("Litre", "L")
        unit_ml = await get_or_create_unit("Millilitre", "ml")
        unit_pcs = await get_or_create_unit("Piece", "pcs")

        # ── Ingredients ───────────────────────────────────────────────────────
        ing_paneer = Ingredient(
            restaurant_id=restaurant.id, name="Paneer",
            unit_id=unit_kg.id, current_stock=Decimal("8.000"),
            low_stock_threshold=Decimal("2.000"), cost_per_unit=Decimal("280.00"),
        )
        ing_chicken = Ingredient(
            restaurant_id=restaurant.id, name="Chicken (boneless)",
            unit_id=unit_kg.id, current_stock=Decimal("12.000"),
            low_stock_threshold=Decimal("3.000"), cost_per_unit=Decimal("220.00"),
        )
        ing_basmati = Ingredient(
            restaurant_id=restaurant.id, name="Basmati Rice",
            unit_id=unit_kg.id, current_stock=Decimal("25.000"),
            low_stock_threshold=Decimal("5.000"), cost_per_unit=Decimal("90.00"),
        )
        ing_cream = Ingredient(
            restaurant_id=restaurant.id, name="Fresh Cream",
            unit_id=unit_litre.id, current_stock=Decimal("3.500"),
            low_stock_threshold=Decimal("1.000"), cost_per_unit=Decimal("180.00"),
        )
        # ⚠️ This one is near low-stock threshold to trigger the alert
        ing_saffron = Ingredient(
            restaurant_id=restaurant.id, name="Saffron",
            unit_id=unit_g.id, current_stock=Decimal("12.000"),
            low_stock_threshold=Decimal("10.000"), cost_per_unit=Decimal("5.00"),
        )
        ing_black_lentils = Ingredient(
            restaurant_id=restaurant.id, name="Black Lentils (Urad Dal)",
            unit_id=unit_kg.id, current_stock=Decimal("15.000"),
            low_stock_threshold=Decimal("3.000"), cost_per_unit=Decimal("85.00"),
        )

        db.add_all([ing_paneer, ing_chicken, ing_basmati, ing_cream, ing_saffron, ing_black_lentils])
        await db.flush()

        # Stock ledger entries for initial purchase
        initial_stock_entries = []
        for ing, qty, note in [
            (ing_paneer, Decimal("8.000"), "Opening stock"),
            (ing_chicken, Decimal("12.000"), "Opening stock"),
            (ing_basmati, Decimal("25.000"), "Opening stock"),
            (ing_cream, Decimal("3.500"), "Opening stock"),
            (ing_saffron, Decimal("12.000"), "Opening stock"),
            (ing_black_lentils, Decimal("15.000"), "Opening stock"),
        ]:
            initial_stock_entries.append(StockLedger(
                restaurant_id=restaurant.id,
                ingredient_id=ing.id,
                quantity_change=qty,
                quantity_before=Decimal("0"),
                quantity_after=qty,
                reason="purchase",
            ))
        db.add_all(initial_stock_entries)

        # ── Recipes ───────────────────────────────────────────────────────────
        # Recipe 1: Paneer Tikka
        recipe_tikka = Recipe(
            restaurant_id=restaurant.id,
            menu_item_id=item_paneer_tikka.id,
            name="Paneer Tikka Recipe",
            yield_quantity=Decimal("1"),
        )
        db.add(recipe_tikka)
        await db.flush()
        db.add_all([
            RecipeIngredient(recipe_id=recipe_tikka.id, ingredient_id=ing_paneer.id,
                             quantity=Decimal("0.250"), unit_id=unit_kg.id),
            RecipeIngredient(recipe_id=recipe_tikka.id, ingredient_id=ing_cream.id,
                             quantity=Decimal("0.050"), unit_id=unit_litre.id),
        ])

        # Recipe 2: Veg Biryani (uses saffron, so served order depletes near-threshold stock)
        recipe_biryani = Recipe(
            restaurant_id=restaurant.id,
            menu_item_id=item_biryani.id,
            name="Hyderabadi Veg Biryani Recipe",
            yield_quantity=Decimal("1"),
        )
        db.add(recipe_biryani)
        await db.flush()
        db.add_all([
            RecipeIngredient(recipe_id=recipe_biryani.id, ingredient_id=ing_basmati.id,
                             quantity=Decimal("0.300"), unit_id=unit_kg.id),
            RecipeIngredient(recipe_id=recipe_biryani.id, ingredient_id=ing_saffron.id,
                             quantity=Decimal("2.000"), unit_id=unit_g.id),  # 2g per plate
        ])

        # Recipe 3: Dal Makhani
        recipe_dal = Recipe(
            restaurant_id=restaurant.id,
            menu_item_id=item_dal_makhani.id,
            name="Dal Makhani Recipe",
            yield_quantity=Decimal("1"),
        )
        db.add(recipe_dal)
        await db.flush()
        db.add_all([
            RecipeIngredient(recipe_id=recipe_dal.id, ingredient_id=ing_black_lentils.id,
                             quantity=Decimal("0.150"), unit_id=unit_kg.id),
            RecipeIngredient(recipe_id=recipe_dal.id, ingredient_id=ing_cream.id,
                             quantity=Decimal("0.030"), unit_id=unit_litre.id),
        ])

        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 6. CRM — customers
        # ══════════════════════════════════════════════════════════════════════
        print("── [6/10] CRM …")

        cust_rohit = Customer(
            restaurant_id=restaurant.id,
            name="Rohit Mehta",
            phone="+919876543210",
            email="rohit.mehta@example.com",
            loyalty_points=250,   # pre-loaded — for redeem testing
            visits_count=5,
        )
        cust_anjali = Customer(
            restaurant_id=restaurant.id,
            name="Anjali Nair",
            phone="+919123456789",
            email="anjali.nair@example.com",
            loyalty_points=0,
            visits_count=1,
        )
        cust_vikram = Customer(
            restaurant_id=restaurant.id,
            name="Vikram Patel",
            phone="+917654321098",
            email=None,
            loyalty_points=50,
            visits_count=2,
        )
        db.add_all([cust_rohit, cust_anjali, cust_vikram])
        await db.flush()   # materialise customer IDs before referencing them below

        # Opening loyalty transaction for Rohit
        db.add(LoyaltyTransaction(
            customer_id=cust_rohit.id,
            restaurant_id=restaurant.id,
            points_change=250,
            transaction_type="accrual",
            description="Opening loyalty balance (demo seed)",
        ))
        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 7. ORDERS — 4 different lifecycle states
        # ══════════════════════════════════════════════════════════════════════
        print("── [7/10] Orders …")

        def _order_item(order_id, item, qty=1, variant_id=None, unit_price=None):
            price = unit_price or item.base_price
            if variant_id:
                # Try to use the variant's price instead
                price = unit_price or item.base_price
            total = price * qty
            oi = OrderItem(
                order_id=order_id,
                menu_item_id=item.id,
                variant_id=variant_id,
                item_name=item.name,
                quantity=qty,
                unit_price=price,
                total_price=total,
            )
            return oi

        def _status_hist(order_id, old, new):
            return OrderStatusHistory(order_id=order_id, old_status=old, new_status=new)

        def _kot(order_id, restaurant_id, branch_id, ticket_num, items_summary):
            return KotTicket(
                order_id=order_id,
                restaurant_id=restaurant_id,
                branch_id=branch_id,
                ticket_number=ticket_num,
                status="new",
                items_json=json.dumps(items_summary),
            )

        # ── ORDER A: dine_in, status=placed ───────────────────────────────────
        subtotal_a = item_paneer_tikka.base_price * 2 + item_lassi.base_price
        tax_a = (subtotal_a * Decimal("5") / 100).quantize(Decimal("0.01"))
        order_placed = Order(
            restaurant_id=restaurant.id,
            branch_id=branch_main.id,
            order_number=_order_number("A01"),
            order_type=OrderType.DINE_IN,
            status=OrderStatus.PLACED,
            table_id=table_main.id,
            waiter_id=user_waiter.id,
            customer_name=cust_anjali.name,
            customer_phone=cust_anjali.phone,
            subtotal=subtotal_a,
            tax_amount=tax_a,
            total_amount=subtotal_a + tax_a,
            inventory_deducted=False,
        )
        db.add(order_placed)
        await db.flush()
        db.add(_status_hist(order_placed.id, None, "placed"))
        db.add(_order_item(order_placed.id, item_paneer_tikka, qty=2))
        db.add(_order_item(order_placed.id, item_lassi, qty=1))
        db.add(_kot(order_placed.id, restaurant.id, branch_main.id,
                    "KOT-A01", [{"item": "Paneer Tikka", "qty": 2}, {"item": "Sweet Lassi", "qty": 1}]))

        # ── ORDER B: takeaway, status=preparing, with variant (Dal Half) ──────
        dal_half_price = Decimal("180.00")
        subtotal_b = dal_half_price + item_masala_chai.base_price
        tax_b = (subtotal_b * Decimal("5") / 100).quantize(Decimal("0.01"))
        order_preparing = Order(
            restaurant_id=restaurant.id,
            branch_id=branch_main.id,
            order_number=_order_number("B02"),
            order_type=OrderType.TAKEAWAY,
            status=OrderStatus.PREPARING,
            customer_name=cust_vikram.name,
            customer_phone=cust_vikram.phone,
            subtotal=subtotal_b,
            tax_amount=tax_b,
            total_amount=subtotal_b + tax_b,
            inventory_deducted=False,
        )
        db.add(order_preparing)
        await db.flush()
        db.add(_status_hist(order_preparing.id, None, "placed"))
        db.add(_status_hist(order_preparing.id, "placed", "confirmed"))
        db.add(_status_hist(order_preparing.id, "confirmed", "preparing"))
        db.add(_order_item(order_preparing.id, item_dal_makhani, qty=1,
                           variant_id=dal_half.id, unit_price=dal_half_price))
        db.add(_order_item(order_preparing.id, item_masala_chai, qty=1))
        db.add(_kot(order_preparing.id, restaurant.id, branch_main.id,
                    "KOT-B02", [{"item": "Dal Makhani (Half)", "qty": 1}]))

        # ── ORDER C: dine_in, status=served, with addon (Biryani + Raita) ─────
        # This order should have inventory deducted
        biryani_price = item_biryani.base_price
        raita_price = addon_raita.price
        biryani_total = (biryani_price + raita_price) * 1
        dal_full_price = Decimal("260.00")
        subtotal_c = biryani_total + dal_full_price
        tax_c = (biryani_total * Decimal("12") / 100 + dal_full_price * Decimal("12") / 100).quantize(Decimal("0.01"))
        order_served = Order(
            restaurant_id=restaurant.id,
            branch_id=branch_main.id,
            order_number=_order_number("C03"),
            order_type=OrderType.DINE_IN,
            status=OrderStatus.SERVED,
            table_id=all_tables[1].id,
            waiter_id=user_waiter.id,
            customer_name=cust_rohit.name,
            customer_phone=cust_rohit.phone,
            subtotal=subtotal_c,
            tax_amount=tax_c,
            total_amount=subtotal_c + tax_c,
            inventory_deducted=True,   # explicitly set to show deduction done
        )
        db.add(order_served)
        await db.flush()
        for old, new in [(None, "placed"), ("placed", "confirmed"), ("confirmed", "preparing"),
                         ("preparing", "ready"), ("ready", "served")]:
            db.add(_status_hist(order_served.id, old, new))

        biryani_oi = OrderItem(
            order_id=order_served.id,
            menu_item_id=item_biryani.id,
            item_name=item_biryani.name,
            quantity=1,
            unit_price=biryani_price,
            total_price=biryani_price + raita_price,
        )
        db.add(biryani_oi)
        await db.flush()

        db.add(OrderAddon(
            order_item_id=biryani_oi.id,
            addon_id=addon_raita.id,
            addon_name=addon_raita.name,
            price=raita_price,
        ))
        db.add(_order_item(order_served.id, item_dal_makhani, qty=1,
                           variant_id=dal_full.id, unit_price=dal_full_price))
        db.add(_kot(order_served.id, restaurant.id, branch_main.id,
                    "KOT-C03", [{"item": "Veg Biryani + Raita", "qty": 1}, {"item": "Dal Makhani (Full)", "qty": 1}]))

        # Deduct inventory for served order (Biryani: 0.3kg rice, 2g saffron)
        ing_basmati.current_stock -= Decimal("0.300")
        ing_saffron.current_stock -= Decimal("2.000")    # now 10.0g — AT the threshold
        ing_black_lentils.current_stock -= Decimal("0.150")
        ing_cream.current_stock -= Decimal("0.030")

        db.add(StockLedger(
            restaurant_id=restaurant.id, ingredient_id=ing_basmati.id,
            quantity_change=Decimal("-0.3000"), quantity_before=Decimal("25.000"),
            quantity_after=Decimal("24.700"), reason="sale",
            reference_id=order_served.id, reference_type="order",
        ))
        db.add(StockLedger(
            restaurant_id=restaurant.id, ingredient_id=ing_saffron.id,
            quantity_change=Decimal("-2.0000"), quantity_before=Decimal("12.000"),
            quantity_after=Decimal("10.000"), reason="sale",
            reference_id=order_served.id, reference_type="order",
        ))
        db.add(StockLedger(
            restaurant_id=restaurant.id, ingredient_id=ing_black_lentils.id,
            quantity_change=Decimal("-0.1500"), quantity_before=Decimal("15.000"),
            quantity_after=Decimal("14.850"), reason="sale",
            reference_id=order_served.id, reference_type="order",
        ))
        db.add(StockLedger(
            restaurant_id=restaurant.id, ingredient_id=ing_cream.id,
            quantity_change=Decimal("-0.0300"), quantity_before=Decimal("3.500"),
            quantity_after=Decimal("3.470"), reason="sale",
            reference_id=order_served.id, reference_type="order",
        ))

        # ── ORDER D: dine_in, status=cancelled ───────────────────────────────
        subtotal_d = item_chicken_tikka.base_price
        tax_d = (subtotal_d * Decimal("5") / 100).quantize(Decimal("0.01"))
        order_cancelled = Order(
            restaurant_id=restaurant.id,
            branch_id=branch_mall.id,
            order_number=_order_number("D04"),
            order_type=OrderType.DINE_IN,
            status=OrderStatus.CANCELLED,
            table_id=all_tables[10].id if len(all_tables) > 10 else all_tables[-1].id,
            customer_name="Walk-in Customer",
            subtotal=subtotal_d,
            tax_amount=tax_d,
            total_amount=subtotal_d + tax_d,
            inventory_deducted=False,
        )
        db.add(order_cancelled)
        await db.flush()
        db.add(_status_hist(order_cancelled.id, None, "placed"))
        db.add(_status_hist(order_cancelled.id, "placed", "cancelled"))
        db.add(_order_item(order_cancelled.id, item_chicken_tikka, qty=1))

        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 8. BILLING — invoice for served order (partial payment)
        # ══════════════════════════════════════════════════════════════════════
        print("── [8/10] Billing …")

        # Real per-item GST at 12% CGST+SGST (intra-state)
        biryani_taxable = biryani_price + raita_price   # ₹360 + ₹50 = ₹410... wait, biryani is 310
        biryani_taxable = item_biryani.base_price + addon_raita.price   # 310 + 50 = 360
        biryani_cgst = (biryani_taxable * Decimal("12") / 100 / 2).quantize(Decimal("0.01"))
        biryani_sgst = biryani_cgst

        dal_taxable = dal_full_price
        dal_cgst = (dal_taxable * Decimal("12") / 100 / 2).quantize(Decimal("0.01"))
        dal_sgst = dal_cgst

        inv_subtotal = biryani_taxable + dal_taxable
        inv_cgst = biryani_cgst + dal_cgst
        inv_sgst = biryani_sgst + dal_sgst
        inv_total_tax = inv_cgst + inv_sgst
        inv_total = inv_subtotal + inv_total_tax

        invoice = Invoice(
            restaurant_id=restaurant.id,
            branch_id=branch_main.id,
            order_id=order_served.id,
            invoice_number=_invoice_number("C03"),
            customer_name=cust_rohit.name,
            customer_phone=cust_rohit.phone,
            subtotal=inv_subtotal,
            cgst_amount=inv_cgst,
            sgst_amount=inv_sgst,
            igst_amount=Decimal("0.00"),
            total_tax=inv_total_tax,
            discount_amount=Decimal("0.00"),
            total_amount=inv_total,
            payment_status=PaymentStatus.PARTIALLY_PAID,
            gst_type=GSTType.CGST_SGST,
        )
        db.add(invoice)
        await db.flush()

        db.add(InvoiceItem(
            invoice_id=invoice.id,
            item_name=f"{item_biryani.name} + {addon_raita.name}",
            hsn_code=item_biryani.hsn_code,
            quantity=1,
            unit_price=biryani_taxable,
            gst_rate=Decimal("12.00"),
            cgst_amount=biryani_cgst,
            sgst_amount=biryani_sgst,
            igst_amount=Decimal("0.00"),
            total_amount=biryani_taxable + biryani_cgst + biryani_sgst,
        ))
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            item_name=f"{item_dal_makhani.name} (Full)",
            hsn_code=item_dal_makhani.hsn_code,
            quantity=1,
            unit_price=dal_taxable,
            gst_rate=Decimal("12.00"),
            cgst_amount=dal_cgst,
            sgst_amount=dal_sgst,
            igst_amount=Decimal("0.00"),
            total_amount=dal_taxable + dal_cgst + dal_sgst,
        ))

        # Partial payment — 50% of total
        partial_amount = (inv_total / 2).quantize(Decimal("0.01"))
        db.add(Payment(
            invoice_id=invoice.id,
            amount=partial_amount,
            method=PaymentMethod.UPI,
            status=PaymentStatus.PAID,
            transaction_id="UPI-DEMO-PARTIAL-001",
            notes="Partial UPI payment (demo)",
        ))

        # GST transaction record
        db.add(GSTTransaction(
            restaurant_id=restaurant.id,
            invoice_id=invoice.id,
            taxable_amount=inv_subtotal,
            cgst_amount=inv_cgst,
            sgst_amount=inv_sgst,
            igst_amount=Decimal("0.00"),
            total_gst=inv_total_tax,
            period_month=date.today().month,
            period_year=date.today().year,
        ))

        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 9. SUBSCRIPTIONS
        # ══════════════════════════════════════════════════════════════════════
        print("── [9/10] Subscriptions ...")

        # Check if plan already exists (global — no restaurant_id)
        res = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.slug == "pro-monthly-demo"))
        plan = res.scalar_one_or_none()
        if not plan:
            plan = SubscriptionPlan(
                name="Pro Monthly (Demo)",
                slug="pro-monthly-demo",
                description="Full-featured plan for multi-branch restaurants",
                price_monthly=Decimal("2999.00"),
                price_yearly=Decimal("29990.00"),
                max_branches=5,
                max_users=50,
                trial_days=14,
                is_active=True,
            )
            db.add(plan)
            await db.flush()

        today = date.today()
        subscription = Subscription(
            restaurant_id=restaurant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            interval=PlanInterval.MONTHLY,
            current_period_start=today,
            current_period_end=today + timedelta(days=30),
            razorpay_subscription_id="sub_demo_XXXXXX",
            razorpay_customer_id="cust_demo_XXXXXX",
        )
        db.add(subscription)
        await db.flush()

        # ══════════════════════════════════════════════════════════════════════
        # 10. FEEDBACK
        # ══════════════════════════════════════════════════════════════════════
        print("── [10/10] Feedback ...")

        feedback = Feedback(
            restaurant_id=restaurant.id,
            order_id=order_served.id,
            customer_id=cust_rohit.id,
            rating=5,
            comments="Excellent biryani! The saffron flavour was perfect. Will definitely come again.",
        )
        db.add(feedback)

        # ── Single commit ─────────────────────────────────────────────────────
        await db.commit()
        print("\n[OK] All seed data committed in a single transaction.\n")

        # ── Print summary ─────────────────────────────────────────────────────
        await _print_summary(db, locals())


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY PRINTER
# ─────────────────────────────────────────────────────────────────────────────
async def _print_summary(db, local_vars: dict | None = None):
    """Print a copy-pasteable summary block."""
    SEP = "=" * 64

    # Fetch from DB to be accurate even if called after --reset
    res = await db.execute(select(Restaurant).where(Restaurant.fssai_number == DEMO_MARKER))
    rest = res.scalar_one_or_none()
    if not rest:
        print("No demo data found.")
        return

    branches = (await db.execute(select(Branch).where(Branch.restaurant_id == rest.id))).scalars().all()
    tables = (await db.execute(select(DiningTable).where(DiningTable.restaurant_id == rest.id).limit(6))).scalars().all()
    await db.execute(select(User).where(User.email.like("%@spiceroute.demo")).union(
        select(User).where(User.email == "superadmin@dineos.demo")
    ))
    orders = (await db.execute(select(Order).where(Order.restaurant_id == rest.id))).scalars().all()
    invoices = (await db.execute(select(Invoice).where(Invoice.restaurant_id == rest.id))).scalars().all()
    customers = (await db.execute(select(Customer).where(Customer.restaurant_id == rest.id))).scalars().all()
    ingredients = (await db.execute(select(Ingredient).where(Ingredient.restaurant_id == rest.id))).scalars().all()

    print(SEP)
    print("   DineOS DEMO SEED -- Summary")
    print(SEP)
    print(f"\n[Restaurant]  {rest.name}  ({rest.id})")
    for b in branches:
        print(f"    Branch [{b.name}]:  {b.id}")
    print(f"\n    Sample table_id (Table 1):  {tables[0].id if tables else 'N/A'}")

    print(f"\n{'-'*64}")
    print("[LOGIN CREDENTIALS]  (all passwords: Password123!)")
    print(f"{'-'*64}")
    print(f"  {'Role':<14}  {'Email':<36}")
    print(f"  {'---':<12}  {'---':<36}")
    role_email_map = {
        "owner":       "owner@spiceroute.demo",
        "manager":     "manager@spiceroute.demo",
        "cashier":     "cashier@spiceroute.demo",
        "waiter":      "waiter@spiceroute.demo",
        "kitchen":     "kitchen@spiceroute.demo",
        "super_admin": "superadmin@dineos.demo",
    }
    for role, email in role_email_map.items():
        print(f"  {role:<14}  {email}")

    print(f"\n{'-'*64}")
    print("[ORDER IDs by Status]")
    print(f"{'-'*64}")
    for o in orders:
        inv_tag = ""
        for inv in invoices:
            if inv.order_id == o.id:
                inv_tag = f"  <- Invoice: {inv.invoice_number} [{inv.payment_status.value}]"
                break
        print(f"  [{o.status.value:<10}]  {o.id}{inv_tag}")

    print(f"\n{'-'*64}")
    print("[Customers with loyalty points (for redeem testing)]")
    print(f"{'-'*64}")
    for c in customers:
        flag = " <- 250 pts pre-loaded" if c.loyalty_points >= 250 else ""
        print(f"  {c.name:<20}  {c.id}  pts={c.loyalty_points}{flag}")

    print(f"\n{'-'*64}")
    print("[WARNING] Ingredient near low-stock threshold (should trigger alert)")
    print(f"{'-'*64}")
    for ing in ingredients:
        if ing.current_stock <= ing.low_stock_threshold * Decimal("1.5"):
            print(f"  [{ing.name}]  stock={float(ing.current_stock):.3f} / threshold={float(ing.low_stock_threshold):.3f}  id={ing.id}")

    print(f"\n{SEP}\n")


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    do_reset = "--reset" in sys.argv
    asyncio.run(seed(reset=do_reset))
