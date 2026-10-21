"""Public information pages. Unconfirmed commercial/legal content is explicit."""
from django.http import Http404
from django.shortcuts import render

PAGES = {'features': ('Features', 'Manage your gym in one place.', 'Directors manage membership approvals and training groups. Coaches track pathways, plan practices, review videos, and communicate with families. Parents can view linked athlete information and contact their gym team.'), 'pricing': ('Pricing', 'Gym pricing is being finalized.', 'No subscription prices or payment commitments are offered on this page yet.'), 'roadmap': ('Roadmap', 'V3: planning and coaching support.', 'Local pilot: daily and weekly gym schedules. Planned: coach briefings, improved video analysis, director insights, and message drafting with human review. Planned features are not available yet and have no committed release date.'), 'help': ('Help Center', 'Getting started', 'Directors create a gym and approve member requests. Athletes, coaches, and parents select their gym during signup. Parents request an athlete link; directors approve it. Directors can use Gym Usage to browse schedules by week or hour.'), 'contact': ('Contact', 'Contact your gym', 'For account access, gym schedules, and athlete questions, sign in and use Messages to contact your director. A public product-support contact has not been configured yet.'), 'support': ('Support', 'Help with your account', 'If you can sign in, send your director a message with the page and problem you encountered. If you cannot sign in, contact your gym through its usual contact details. Do not share passwords. Public product-support contact details are still to be added.'), 'privacy': ('Privacy', 'Privacy notice — draft placeholder', 'The final privacy notice has not been published. Data collection, service providers, retention, access requests, and contact information must be confirmed before this page can serve as a complete privacy policy.'), 'terms': ('Terms', 'Terms — draft placeholder', 'The final terms of use have not been published. This page is not a completed agreement. Operator details, service terms, account responsibilities, and commercial terms still need to be finalized.'), 'cookies': ('Cookies', 'Cookie notice — draft placeholder', 'The final cookie notice has not been published. The deployed site’s cookies and third-party services must be reviewed before publishing an accurate notice.')}


def public_info(request, slug):
    if slug not in PAGES:
        raise Http404
    title, heading, body = PAGES[slug]
    return render(request, 'public_info.html', {
        'title': title, 'heading': heading, 'body': body,
    })
