"""Starting content for a new database.

`flask --app app init-db` copies the carriers, coverage and people below into the database
the first time it runs. After that, agents change them in the portal (Website section), and
edits here only matter for a brand-new database. Request topics and quote choices are still
read from here because the forms validate against them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Agency:
    name: str
    street: str
    city: str
    region: str
    postcode: str
    phone_display: str
    phone_dial: str
    second_phone_display: str
    second_phone_dial: str
    email: str
    map_url: str


@dataclass(frozen=True)
class Coverage:
    slug: str
    name: str
    headline: str
    summary: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Paperwork:
    slug: str
    label: str
    use: str


@dataclass(frozen=True)
class Carrier:
    slug: str
    name: str
    logo_height: int
    website: str
    claims_display: str
    claims_dial: str
    billing_display: str
    billing_dial: str


AGENCY = Agency(
    name="Otto & Associates",
    street="6650 Kilbourne Rd.",
    city="Sunbury",
    region="OH",
    postcode="43074",
    # The office line is the main number; the second is the agents' cell.
    phone_display="(937) 545-6148",
    phone_dial="+19375456148",
    second_phone_display="(937) 610-0088",
    second_phone_dial="+19376100088",
    email="andi@theottoagency.com",
    map_url="https://www.google.com/maps/search/?api=1&query=6650+Kilbourne+Rd+Sunbury+OH+43074",
)

# Ways to meet. The agency works from home, so in-person visits are arranged case by case.
MEETING_KINDS = {
    "phone": "Phone call",
    "video": "Video call",
    "in-person": "In person, by arrangement",
}

# The quote builder on the home page. Slug -> (word in the sentence, what to quote).
QUOTE_ITEMS = {
    "home": ("home", "Homeowners"),
    "renters": ("apartment", "Renters"),
    "rental": ("rental property", "Landlord package"),
    "car": ("car", "Auto"),
    "motorcycle": ("motorcycle", "Motorcycle"),
    "boat": ("boat", "Boat"),
    "camper": ("camper", "Travel trailer or motorhome"),
    "umbrella": ("savings", "Umbrella liability"),
    "business": ("business", "Business"),
}

COVERAGE = (
    Coverage(
        "home",
        "Home and property",
        "Your home is probably your biggest asset",
        "No two homes or owners are alike, so we quote several companies and find the policy that "
        "puts you back where you were after a loss, at a price that suits you.",
        ("Homeowners", "Renters", "Condominium", "Landlord packages for rentals", "Vacant property"),
    ),
    Coverage(
        "auto",
        "Auto",
        "When there is an accident, we stay on it",
        "We do not just hand you to a claims adjuster. Whatever your driving record, we find the "
        "right company and help until the claim is resolved.",
        ("Preferred drivers", "Standard drivers", "Non-standard and high-risk drivers", "SR22 bonds"),
    ),
    Coverage(
        "toys",
        "Toys",
        "Protect the things you worked hard for",
        "Boats, motorcycles, campers and ATVs need their own cover. We work with companies that "
        "specialise in them.",
        ("Boats", "Motorcycles", "Travel trailers and motorhomes", "ATVs and other recreational vehicles"),
    ),
    Coverage(
        "umbrella",
        "Umbrella",
        "Extra protection if you are ever sued",
        "An umbrella policy pays for court costs and counsel, and adds liability limits above your "
        "home and auto policies. It costs little for what it covers.",
        ("Higher liability limits", "Court costs and legal counsel", "Sits above home, auto and toys"),
    ),
    Coverage(
        "business",
        "Business",
        "Coverage for every stage of your business",
        "A family firm with many employees or a one-person start-up: tell us what you do and we "
        "will find the coverage that fits.",
        ("Business package policies", "Key person policies", "Business auto", "Contractor packages"),
    ),
)

PAPERWORK_ITEMS = (
    Paperwork("proof-card", "Proof of insurance card", "For your glovebox, the BMV or a traffic stop"),
    Paperwork("declarations", "Declarations page", "A summary of what your policy covers"),
    Paperwork("certificate", "Certificate of insurance", "For contracts, landlords and job sites"),
    Paperwork("verification", "Verification of insurance", "Proof for a lender, dealer or employer"),
)

# Topic slug -> label. The slug is what the home page links use in ?topic=.
REQUEST_TOPICS = {
    "proof-card": "Proof of insurance card",
    "declarations": "Declarations page",
    "certificate": "Certificate of insurance",
    "verification": "Verification of insurance",
    "quote": "A quote",
    "payment": "A payment",
    "feedback": "Feedback",
    "other": "Something else",
}

PAPERWORK = ("proof-card", "declarations", "certificate", "verification")

CARRIERS = (
    Carrier("grange", "Grange", 54, "https://www.grangeinsurance.com/", "1-800-422-0550", "+18004220550", "1-800-422-0550", "+18004220550"),
    Carrier("progressive", "Progressive", 24, "https://www.progressive.com/", "1-800-776-4737", "+18007764737", "1-877-776-2436", "+18777762436"),
    Carrier("encompass", "Encompass", 40, "https://www.encompassinsurance.com/", "1-800-588-7400", "+18005887400", "1-866-430-2916", "+18664302916"),
    Carrier("mapfre", "MAPFRE", 19, "https://www.mapfreinsurance.com/", "1-877-224-5677", "+18772245677", "1-800-222-2114", "+18002222114"),
    Carrier("foremost", "Foremost", 38, "https://www.foremost.com/", "1-800-527-3905", "+18005273905", "1-800-532-4221", "+18005324221"),
    Carrier("trexis", "Trexis", 50, "https://www.trexis.com/", "1-877-584-7466", "+18775847466", "1-877-384-7466", "+18773847466"),
    Carrier("commonwealth", "Commonwealth", 30, "https://www.commonwealthcasualty.com/", "1-877-603-1310", "+18776031310", "1-877-603-1310", "+18776031310"),
    Carrier("national-general", "National General", 52, "https://www.nationalgeneral.com/", "1-800-468-3466", "+18004683466", "1-800-462-2123", "+18004622123"),
)

RECOGNITION = (
    ("J.D. Power customer service award", "American Family years"),
    ("Business Person of the Year", "Huber Heights Chamber"),
)

COMMUNITY = (
    "Wayne Pee Wee Football",
    "Huber Heights Little League",
    "Wayne Soccer Club",
    "Wayne Wrestling Club",
    "Huber Heights Chamber of Commerce",
    "Huber Heights F&AM Lodge 777",
    "Relay For Life",
    "Valley Forge PTO",
    "Huber Heights Community Event Foundation",
)
