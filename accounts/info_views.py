"""Public product information; commercial and operational promises stay explicit."""
from django.conf import settings
from django.http import Http404
from django.shortcuts import render

PAGES = {
    'features': ('Features', 'A coaching workspace for your gymnastics program.',
                 'Bring athlete check-ins, coaching records and family communication together.'),
    'pricing': ('Pricing & pilots', 'Discuss the right fit for your gym.',
                'Fixed subscription plans and pilot terms are not published yet. Ask about pricing and evaluation options for your program before deciding.'),
    'roadmap': ('Roadmap', 'Coaching tools, with room to grow.',
                'Planned: coach briefings, improved video analysis, director insights and message drafting with human review. Planned features are not available yet and have no committed release date.'),
    'help': ('Help Center', 'Getting started',
             'Directors create a gym and approve member requests. Athletes, coaches and parents select their gym during signup. Parents request an athlete link; directors approve it.'),
    'support': ('Support', 'Get help with the right team.',
                'For schedules, athlete questions and membership approvals, contact your gym. For product issues or questions about NewSchool, use the public enquiry form.'),
    'privacy': ('Data & privacy', 'Understand how information is used.',
                'NewSchool supports gym operations, coaching and family communication. This page describes information handled by the application and how to ask questions about it.'),
    'terms': ('Terms', 'Terms — draft placeholder',
              'The final terms of use have not been published. This page is not a completed agreement. Operator details, service terms, account responsibilities and commercial terms still need to be finalized.'),
    'cookies': ('Cookies', 'Cookies and external resources',
                'The application uses session cookies for sign-in and form protection cookies to help prevent forged submissions. Public forms also use the session to limit repeated enquiries. These pages load Bootstrap resources from jsDelivr, which receives connection information when your browser requests them.'),
}

SECTIONS = {
    'features': [
        ('Practice Passports and learning quests', 'Coach-approved stamps recognize personal progress, skill learning and teamwork. Optional quests encourage questions and reflection. Wellness answers, journal entries and safety reports do not determine Passport eligibility; breaks do not reset earned stamps.'),
        ('Clear communication routes', 'Athletes message coaches only, with an explicitly selected approved parent or second coach included. Parents and coaches can contact directors. Participants see who is included in the new thread. Older one-to-one athlete conversations remain read-only and are not automatically shared.'),
        ('Directors: organize your gym', 'Manage training groups, coaches and athletes. Approve membership requests and parent-to-athlete connections.'),
        ('Coaches: keep training context together', 'Review daily check-ins, record attendance, follow skills and testing, add athlete notes and review videos.'),
        ('Athletes and families: follow progress', 'Athletes complete check-ins and review feedback. Parents can access information for approved linked athletes and communicate with their gym team.'),
        ('Works alongside registration and billing', 'NewSchool focuses on coaching and athlete development. Registration, payments and automated integrations are not part of this offer.'),
        ('Video analysis availability', 'Playback and coach feedback are coaching tools. AI-assisted frame and pose analysis is experimental, depends on processing setup and footage, and requires coach review. Ask to see the current tools in a demo.'),
    ],
    'pricing': [
        ('Start with a demo enquiry', 'Tell us about your gym and what you want to explore. The team reviews your request and uses your email to arrange a conversation. Sending an enquiry does not create an account or start a paid subscription.'),
        ('Clarify the terms before a pilot', 'Discuss the included features, number of users, any pilot duration, costs, support, cancellation and how your data is handled. No free pilot, fixed price or service commitment is advertised here.'),
        ('Plan setup around your program', 'A director sets up the gym, training groups and roster, then approves members and parent connections. Discuss setup assistance and import needs before starting. Automatic migration is not promised.'),
    ],
    'support': [
        ('Gym and athlete questions', 'Sign in to Messages or contact your gym through its usual contact details. Your director manages membership approvals and parent connections.'),
        ('Product support', 'Use the contact form for a product issue. Include the page, your role and what happened. Do not include passwords, reset links, athlete wellness details or private videos.'),
    ],
    'privacy': [
        ('Athlete conversations and observer access', 'All athlete accounts use supervised messaging, without relying on an age assumption. A new athlete-coach thread includes an explicitly selected approved linked parent or second coach. Everyone in that thread can read it. The application records its participants and observer. Earlier one-to-one conversations are not automatically shared with new people. A revoked parent connection removes access to related message threads and their notification previews.'),
        ('Information used by the app', 'Depending on the features your gym uses, the application stores account and contact details, gym memberships and groups, athlete profiles, parent connections, daily wellness responses, attendance, skill and testing results, coach notes, messages, journal entries, and uploaded videos and feedback. Some information, such as wellness responses and videos, can be sensitive.'),
        ('Why information is used', 'These records support account access, gym membership management, coaching, training history and communication with families. Your gym chooses how it uses the platform and should explain its approach to athletes and guardians.'),
        ('Who can access information', 'Access depends on gym membership, role, assignments, approved parent connections and feature-specific sharing settings. Parents need an approved athlete connection. A private note or journal entry is not automatically shared with families. Authorized platform administrators can administer the service; access controls are not a guarantee that no incident can occur.'),
        ('Your choices and requests', 'Ask your gym director about the information your gym records and the consent process for athletes, guardians and videos. Use the product contact form to request information about access, correction or deletion, or raise a privacy concern. Do not include sensitive athlete details in the initial enquiry. Identity and authority may need to be checked before records can be discussed or changed.'),
    ],
}


def public_info(request, slug):
    if slug not in PAGES:
        raise Http404
    title, heading, body = PAGES[slug]
    sections = list(SECTIONS.get(slug, []))
    if slug == 'privacy':
        storage = 'Supabase Storage' if settings.USE_SUPABASE_STORAGE else 'the application’s configured media storage'
        sections.extend([
            ('Hosting and service providers', f'The public app is hosted on Render. Uploaded media uses {storage}. Where enabled, report and account-recovery emails use Resend. These public pages load Bootstrap from jsDelivr. Ask the product team to confirm the provider list, hosting regions and processing arrangements applicable to your gym.'),
            ('Retention and deletion', 'A complete retention schedule, including account records, athlete records, enquiries, uploaded media and backups, still needs to be finalized by the operator. Do not assume that closing an account immediately removes every record or backup. Request the applicable retention and deletion arrangements before onboarding your gym.'),
        ])
    return render(request, 'public_info.html', {
        'title': title, 'heading': heading, 'body': body, 'slug': slug, 'sections': sections,
    })
