"""create_districts_table_and_link_users

Revision ID: d54e12a91f33
Revises: c83e10d94f21
Create Date: 2026-11-02 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd54e12a91f33'
down_revision: Union[str, Sequence[str], None] = 'c83e10d94f21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SRI_LANKAN_DISTRICTS = [
    # Western Province
    {"id": 1, "code": "COLOMBO", "name_en": "Colombo", "name_si": "කොළඹ", "name_ta": "கொழும்பு", "province": "WESTERN", "display_order": 1},
    {"id": 2, "code": "GAMPAHA", "name_en": "Gampaha", "name_si": "ගම්පහ", "name_ta": "கம்பஹா", "province": "WESTERN", "display_order": 2},
    {"id": 3, "code": "KALUTARA", "name_en": "Kalutara", "name_si": "කළුතර", "name_ta": "களுத்துறை", "province": "WESTERN", "display_order": 3},
    # Central Province
    {"id": 4, "code": "KANDY", "name_en": "Kandy", "name_si": "මහනුවර", "name_ta": "கண்டி", "province": "CENTRAL", "display_order": 4},
    {"id": 5, "code": "MATALE", "name_en": "Matale", "name_si": "මාතලේ", "name_ta": "மாத்தளை", "province": "CENTRAL", "display_order": 5},
    {"id": 6, "code": "NUWARA_ELIYA", "name_en": "Nuwara Eliya", "name_si": "නුවරඑළිය", "name_ta": "நுவரெலியா", "province": "CENTRAL", "display_order": 6},
    # Southern Province
    {"id": 7, "code": "GALLE", "name_en": "Galle", "name_si": "ගාල්ල", "name_ta": "காலி", "province": "SOUTHERN", "display_order": 7},
    {"id": 8, "code": "MATARA", "name_en": "Matara", "name_si": "මාතර", "name_ta": "மாத்தறை", "province": "SOUTHERN", "display_order": 8},
    {"id": 9, "code": "HAMBANTOTA", "name_en": "Hambantota", "name_si": "හම්බන්තොට", "name_ta": "அம்பாந்தோட்டை", "province": "SOUTHERN", "display_order": 9},
    # Northern Province
    {"id": 10, "code": "JAFFNA", "name_en": "Jaffna", "name_si": "යාපනය", "name_ta": "யாழ்ப்பாணம்", "province": "NORTHERN", "display_order": 10},
    {"id": 11, "code": "KILINOCHCHI", "name_en": "Kilinochchi", "name_si": "කිලිනොච්චිය", "name_ta": "கிளிநொச்சி", "province": "NORTHERN", "display_order": 11},
    {"id": 12, "code": "MANNAR", "name_en": "Mannar", "name_si": "මන්නාරම", "name_ta": "மன்னார்", "province": "NORTHERN", "display_order": 12},
    {"id": 13, "code": "VAVUNIYA", "name_en": "Vavuniya", "name_si": "වවුනියාව", "name_ta": "வவுனியா", "province": "NORTHERN", "display_order": 13},
    {"id": 14, "code": "MULLAITIVU", "name_en": "Mullaitivu", "name_si": "මුලතිව්", "name_ta": "முல்லைத்தீவு", "province": "NORTHERN", "display_order": 14},
    # Eastern Province
    {"id": 15, "code": "BATTICALOA", "name_en": "Batticaloa", "name_si": "මඩකලපුව", "name_ta": "மட்டக்களப்பு", "province": "EASTERN", "display_order": 15},
    {"id": 16, "code": "AMPARA", "name_en": "Ampara", "name_si": "අම්පාර", "name_ta": "அம்பாறை", "province": "EASTERN", "display_order": 16},
    {"id": 17, "code": "TRINCOMALEE", "name_en": "Trincomalee", "name_si": "ත්‍රිකුණාමලය", "name_ta": "திருகோணமலை", "province": "EASTERN", "display_order": 17},
    # North Western Province
    {"id": 18, "code": "KURUNEGALA", "name_en": "Kurunegala", "name_si": "කුරුණෑගල", "name_ta": "குருணாகல்", "province": "NORTH_WESTERN", "display_order": 18},
    {"id": 19, "code": "PUTTALAM", "name_en": "Puttalam", "name_si": "පුත්තලම", "name_ta": "புத்தளம்", "province": "NORTH_WESTERN", "display_order": 19},
    # North Central Province
    {"id": 20, "code": "ANURADHAPURA", "name_en": "Anuradhapura", "name_si": "අනුරාධපුරය", "name_ta": "அனுராதபுரம்", "province": "NORTH_CENTRAL", "display_order": 20},
    {"id": 21, "code": "POLONNARUWA", "name_en": "Polonnaruwa", "name_si": "පොළොන්නරුව", "name_ta": "பொலன்னறுவை", "province": "NORTH_CENTRAL", "display_order": 21},
    # Uva Province
    {"id": 22, "code": "BADULLA", "name_en": "Badulla", "name_si": "බදුල්ල", "name_ta": "பதுளை", "province": "UVA", "display_order": 22},
    {"id": 23, "code": "MONARAGALA", "name_en": "Monaragala", "name_si": "මොනරාගල", "name_ta": "மொணරාகலை", "province": "UVA", "display_order": 23},
    # Sabaragamuwa Province
    {"id": 24, "code": "RATNAPURA", "name_en": "Ratnapura", "name_si": "රත්නපුර", "name_ta": "இரத்தினபுரி", "province": "SABARAGAMUWA", "display_order": 24},
    {"id": 25, "code": "KEGALLE", "name_en": "Kegalle", "name_si": "කෑගල්ල", "name_ta": "கேகாலை", "province": "SABARAGAMUWA", "display_order": 25},
]


def upgrade() -> None:
    """Create districts lookup table with integer PK (1-25) & code slug, seed 25 districts, and link users."""
    # 1. Create districts table
    districts_table = op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_si', sa.String(length=100), nullable=False),
        sa.Column('name_ta', sa.String(length=100), nullable=False),
        sa.Column('province', sa.String(length=50), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_districts_code'), 'districts', ['code'], unique=True)
    op.create_index(op.f('ix_districts_province'), 'districts', ['province'], unique=False)

    # 2. Pre-seed 25 Sri Lankan Districts
    op.bulk_insert(districts_table, SRI_LANKAN_DISTRICTS)

    # 3. Add district_id integer foreign key column to users
    op.add_column('users', sa.Column('district_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_users_district_id_districts',
        'users',
        'districts',
        ['district_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_users_district_id'), 'users', ['district_id'], unique=False)

    # 4. Migrate any matching text in legacy 'district' column if exists
    op.execute("""
        UPDATE users u
        SET district_id = d.id
        FROM districts d
        WHERE u.district IS NOT NULL
          AND (UPPER(TRIM(u.district)) = d.code OR UPPER(TRIM(u.district)) = UPPER(d.name_en));
    """)

    # 5. Drop legacy district column
    op.drop_column('users', 'district')


def downgrade() -> None:
    """Revert users foreign key and drop districts lookup table."""
    op.add_column('users', sa.Column('district', sa.String(length=100), nullable=True))
    op.execute("""
        UPDATE users u
        SET district = d.code
        FROM districts d
        WHERE u.district_id = d.id;
    """)
    op.drop_constraint('fk_users_district_id_districts', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_district_id'), table_name='users')
    op.drop_column('users', 'district_id')
    op.drop_index(op.f('ix_districts_province'), table_name='districts')
    op.drop_index(op.f('ix_districts_code'), table_name='districts')
    op.drop_table('districts')
