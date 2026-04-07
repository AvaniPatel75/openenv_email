"""
Email corpus for the triage environment.
Each email has ground-truth labels for grading.
"""

from typing import Optional
from pydantic import BaseModel


class EmailData(BaseModel):
    id: str
    subject: str
    body: str
    sender: str
    sender_domain: str
    # Ground truth labels
    true_urgency: str          # low, medium, high, critical
    true_category: str         # billing, technical, general, complaint, praise
    true_department: str       # billing, engineering, sales, support, escalation
    true_priority: int         # 1 (lowest) to 5 (highest)
    requires_escalation: bool
    key_issues: list[str]      # things a good reply must address
    expected_tone: str         # empathetic, professional, apologetic, positive


EMAILS: list[EmailData] = [
    EmailData(
        id="email_001",
        subject="URGENT: Production database down - losing $10k/minute",
        body=(
            "Our production database has been completely unreachable for the past 45 minutes. "
            "We are a paying enterprise customer (account #ENT-8821) and this is causing severe "
            "revenue loss estimated at $10,000 per minute. Every minute counts. Our CTO is on the "
            "phone with our board right now. We need someone with database admin access to engage "
            "IMMEDIATELY. This is not acceptable. If this is not resolved in the next 30 minutes "
            "we will be terminating our contract and pursuing legal remedies. "
            "Contact: Mike Chen, CTO - mike.chen@acmecorp.com - +1-415-555-0192"
        ),
        sender="mike.chen@acmecorp.com",
        sender_domain="acmecorp.com",
        true_urgency="critical",
        true_category="technical",
        true_department="escalation",
        true_priority=5,
        requires_escalation=True,
        key_issues=[
            "production outage",
            "enterprise customer",
            "revenue loss quantified",
            "legal threat",
            "direct contact provided",
        ],
        expected_tone="apologetic",
    ),
    EmailData(
        id="email_002",
        subject="Double charged on my invoice this month",
        body=(
            "Hi, I noticed that I was charged twice for my subscription this month. "
            "My account email is sarah@freelancedesign.com and I'm on the Pro plan ($49/month). "
            "I see two charges of $49 on June 14th in my bank statement. "
            "Can you please refund one of them? I've been a customer for 3 years and this is "
            "the first time this has happened. Thank you!"
        ),
        sender="sarah@freelancedesign.com",
        sender_domain="freelancedesign.com",
        true_urgency="medium",
        true_category="billing",
        true_department="billing",
        true_priority=3,
        requires_escalation=False,
        key_issues=[
            "duplicate charge identified",
            "account details provided",
            "loyal customer mentioned",
            "specific dates and amounts given",
        ],
        expected_tone="empathetic",
    ),
    EmailData(
        id="email_003",
        subject="How do I export my data to CSV?",
        body=(
            "Hello, I'm trying to export my project data to CSV format for a presentation "
            "next week. I looked at the documentation but couldn't find clear instructions. "
            "I'm using the Business plan. Is this feature available and if so, how do I access it? "
            "Thanks in advance!"
        ),
        sender="james.wu@techstartup.io",
        sender_domain="techstartup.io",
        true_urgency="low",
        true_category="general",
        true_department="support",
        true_priority=2,
        requires_escalation=False,
        key_issues=[
            "feature availability question",
            "documentation gap noted",
            "specific use case given",
        ],
        expected_tone="professional",
    ),
    EmailData(
        id="email_004",
        subject="Your app is absolutely incredible - saved our team 20 hours/week",
        body=(
            "I just wanted to take a moment to say how much your product has transformed "
            "our workflow. Since we started using it 6 months ago, we've saved an estimated "
            "20 hours per week across our 12-person team. The automation features are "
            "particularly outstanding. We've already recommended you to 5 other companies in "
            "our network. Keep up the amazing work! - Priya, Head of Operations at NovaTech"
        ),
        sender="priya.sharma@novatech.com",
        sender_domain="novatech.com",
        true_urgency="low",
        true_category="praise",
        true_department="support",
        true_priority=1,
        requires_escalation=False,
        key_issues=[
            "positive feedback",
            "specific metrics provided",
            "referrals mentioned",
            "relationship building opportunity",
        ],
        expected_tone="positive",
    ),
    EmailData(
        id="email_005",
        subject="API rate limits are completely unreasonable - considering switching",
        body=(
            "Your API rate limits are making our product unusable. We're hitting the limit "
            "of 1000 calls/hour constantly, and our application requires at least 5000/hour "
            "to function properly. We're on the Growth plan at $199/month. "
            "I've submitted two support tickets (TKT-4421 and TKT-4587) in the past month "
            "and gotten no resolution. We're actively evaluating your competitors. "
            "I need an answer within 24 hours or we're leaving. "
            "- Alex Rivera, Lead Engineer"
        ),
        sender="alex.rivera@dataflow.ai",
        sender_domain="dataflow.ai",
        true_urgency="high",
        true_category="complaint",
        true_department="engineering",
        true_priority=4,
        requires_escalation=True,
        key_issues=[
            "technical limitation blocking product",
            "prior unresolved tickets referenced",
            "churn risk stated explicitly",
            "24 hour deadline given",
            "upgrade path needed",
        ],
        expected_tone="empathetic",
    ),
    EmailData(
        id="email_006",
        subject="Need receipt for Q2 expenses - tax deadline tomorrow",
        body=(
            "Hi, I urgently need a receipt/invoice for all charges from April through June "
            "for our company account. Our account manager is on vacation and our tax filing "
            "deadline is tomorrow morning. Account ID: BIZ-2934. "
            "Please send to finance@globalretail.com as soon as possible. "
            "This is time-sensitive!"
        ),
        sender="controller@globalretail.com",
        sender_domain="globalretail.com",
        true_urgency="high",
        true_category="billing",
        true_department="billing",
        true_priority=4,
        requires_escalation=False,
        key_issues=[
            "time-sensitive tax deadline",
            "account number provided",
            "specific date range requested",
            "alternate email for delivery",
        ],
        expected_tone="professional",
    ),
    EmailData(
        id="email_007",
        subject="Integration with Salesforce not syncing correctly",
        body=(
            "We set up the Salesforce integration last Tuesday and it's not syncing our "
            "contact records properly. About 30% of new leads aren't being pulled through. "
            "We followed the setup guide exactly. Our Salesforce version is Enterprise 2024. "
            "This is affecting our sales team's pipeline visibility. "
            "Happy to do a screen share if that helps troubleshoot."
        ),
        sender="ben.okafor@growthco.com",
        sender_domain="growthco.com",
        true_urgency="medium",
        true_category="technical",
        true_department="engineering",
        true_priority=3,
        requires_escalation=False,
        key_issues=[
            "integration bug with specific version",
            "percentage of failure quantified",
            "business impact described",
            "willingness to collaborate on fix",
        ],
        expected_tone="professional",
    ),
    EmailData(
        id="email_008",
        subject="Interested in upgrading to Enterprise - pricing question",
        body=(
            "Hi, we're currently on the Business plan and have been happy customers for "
            "18 months. Our team has grown from 8 to 45 people and we're hitting limits. "
            "Could someone from your sales team reach out to discuss Enterprise pricing "
            "and volume discounts? We'd also like to understand SSO and custom integrations. "
            "Best time to chat: Mon-Wed mornings PST. - Director of Engineering"
        ),
        sender="director.eng@scaleup.com",
        sender_domain="scaleup.com",
        true_urgency="medium",
        true_category="general",
        true_department="sales",
        true_priority=3,
        requires_escalation=False,
        key_issues=[
            "expansion opportunity",
            "specific features of interest listed",
            "availability provided",
            "long-term customer",
        ],
        expected_tone="positive",
    ),
]

# Triage task uses a curated queue of 5 emails
TRIAGE_QUEUE_IDS = ["email_001", "email_002", "email_003", "email_005", "email_006"]

# Respond task uses a complex complaint that needs careful handling
RESPOND_TARGET_ID = "email_005"

def get_email_by_id(email_id: str) -> Optional[EmailData]:
    for e in EMAILS:
        if e.id == email_id:
            return e
    return None

def get_triage_queue() -> list[EmailData]:
    return [e for e in EMAILS if e.id in TRIAGE_QUEUE_IDS]
