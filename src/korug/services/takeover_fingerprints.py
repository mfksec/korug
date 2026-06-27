"""Service fingerprints for precise subdomain-takeover detection.

Attribution
-----------
The service CNAME patterns and "unclaimed" page fingerprints below are derived
from the community project **can-i-take-over-xyz** by EdOverflow and contributors
(https://github.com/EdOverflow/can-i-take-over-xyz), which is licensed
**CC BY-SA 4.0**. This curated subset is therefore a derivative work and is shared
under the same CC BY-SA 4.0 terms. Thanks to that project and its contributors.
See the Acknowledgements section of the project README.

A curated set of third-party services that are takeover-prone when a dangling
CNAME points at them. Each entry pairs:

- ``cnames``   — substrings that identify the service in a CNAME target, and
- ``fingerprints`` — substrings that appear in the HTTP body of an *unclaimed*
  target (the "claim this / not found" page).

Detection is precise because it requires **both** a CNAME match and either the
target being unresolvable (NXDOMAIN) or a body fingerprint hit — not merely a
CNAME that happens to point at a SaaS provider. ``vulnerable`` is ``True`` for
services where a fingerprint match is a confirmed takeover, or ``"edge"`` for
services that need manual verification (claim flow varies / often not takeoverable).

Amazon S3 is intentionally absent here — it has a dedicated, authoritative
bucket-existence check in ``takeover_detection.py``.
"""
from typing import Dict, List

FINGERPRINTS: List[Dict] = [
    {"service": "GitHub Pages", "cnames": ["github.io", "github.map.fastly.net"],
     "fingerprints": ["There isn't a GitHub Pages site here.",
                      "For root URLs (like http://example.com/) you must provide an index.html file"],
     "vulnerable": True},
    {"service": "Bitbucket", "cnames": ["bitbucket.io"],
     "fingerprints": ["Repository not found"], "vulnerable": True},
    {"service": "Ghost", "cnames": ["ghost.io"],
     "fingerprints": ["The thing you were looking for is no longer here, or never was"], "vulnerable": True},
    {"service": "Help Scout", "cnames": ["helpscoutdocs.com"],
     "fingerprints": ["No settings were found for this company:"], "vulnerable": True},
    {"service": "Helpjuice", "cnames": ["helpjuice.com"],
     "fingerprints": ["We could not find what you're looking for."], "vulnerable": True},
    {"service": "JetBrains YouTrack", "cnames": ["myjetbrains.com"],
     "fingerprints": ["is not a registered InCloud YouTrack"], "vulnerable": True},
    {"service": "Pantheon", "cnames": ["pantheonsite.io"],
     "fingerprints": ["The gods are wise, but do not know of the site which you seek.",
                      "404 error unknown site!"], "vulnerable": True},
    {"service": "Readme.io", "cnames": ["readme.io"],
     "fingerprints": ["Project doesnt exist... yet!"], "vulnerable": True},
    {"service": "Surge.sh", "cnames": ["surge.sh"],
     "fingerprints": ["project not found"], "vulnerable": True},
    {"service": "Tumblr", "cnames": ["domains.tumblr.com"],
     "fingerprints": ["Whatever you were looking for doesn't currently exist at this address.",
                      "There's nothing here."], "vulnerable": True},
    {"service": "UserVoice", "cnames": ["uservoice.com"],
     "fingerprints": ["This UserVoice subdomain is currently available!"], "vulnerable": True},
    {"service": "Strikingly", "cnames": ["s.strikinglydns.com"],
     "fingerprints": ["But if you're looking to build your own website",
                      "page not found"], "vulnerable": True},
    {"service": "Smartling", "cnames": ["smartling.com"],
     "fingerprints": ["Domain is not configured"], "vulnerable": True},
    {"service": "Wishpond", "cnames": ["wishpond.com"],
     "fingerprints": ["https://www.wishpond.com/404?campaign=true"], "vulnerable": True},
    {"service": "Aftership", "cnames": ["aftership.com"],
     "fingerprints": ["Oops.</h2><p class=\"text-muted\">The page you're looking for doesn't exist."],
     "vulnerable": True},
    {"service": "Aha!", "cnames": ["ideas.aha.io"],
     "fingerprints": ["There is no portal here ... sending you back to Aha!"], "vulnerable": True},
    {"service": "Agile CRM", "cnames": ["agilecrm.com"],
     "fingerprints": ["Sorry, this page is no longer available."], "vulnerable": True},
    {"service": "Anima", "cnames": ["animaapp.io"],
     "fingerprints": ["If this is your website and you've just created it"], "vulnerable": True},
    {"service": "Big Cartel", "cnames": ["bigcartel.com"],
     "fingerprints": ["<h1>Oops! We couldn&#8217;t find that page.</h1>"], "vulnerable": True},
    {"service": "Canny", "cnames": ["canny.io"],
     "fingerprints": ["Company Not Found",
                      "There is no such company. Did you enter the right URL?"], "vulnerable": True},
    {"service": "Feedpress", "cnames": ["redirect.feedpress.me"],
     "fingerprints": ["The feed has not been found."], "vulnerable": True},
    {"service": "GetResponse", "cnames": ["gr8.com"],
     "fingerprints": ["With GetResponse Landing Pages, lead generation has never been easier"],
     "vulnerable": True},
    {"service": "LaunchRock", "cnames": ["launchrock.com"],
     "fingerprints": ["It looks like you may have taken a wrong turn somewhere. "
                      "Don't worry...it happens to all of us."], "vulnerable": True},
    {"service": "Ngrok", "cnames": ["ngrok.io"],
     "fingerprints": ["Tunnel *.ngrok.io not found", "ngrok.io not found"], "vulnerable": True},
    {"service": "Worksites", "cnames": ["worksites.net"],
     "fingerprints": ["Hello! Sorry, but the website you&#8217;re looking for doesn&#8217;t exist."],
     "vulnerable": True},
    # Edge cases — fingerprint match is suggestive but the claim flow varies, so
    # treat as "verify manually" rather than a confirmed takeover.
    {"service": "Heroku", "cnames": ["herokuapp.com", "herokudns.com", "herokussl.com"],
     "fingerprints": ["No such app", "herokucdn.com/error-pages/no-such-app.html"], "vulnerable": "edge"},
    {"service": "Shopify", "cnames": ["myshopify.com"],
     "fingerprints": ["Sorry, this shop is currently unavailable."], "vulnerable": "edge"},
    {"service": "Fastly", "cnames": ["fastly.net"],
     "fingerprints": ["Fastly error: unknown domain"], "vulnerable": "edge"},
    {"service": "Tilda", "cnames": ["tilda.ws"],
     "fingerprints": ["Domain has been assigned"], "vulnerable": "edge"},
    {"service": "Wordpress", "cnames": ["wordpress.com"],
     "fingerprints": ["Do you want to register"], "vulnerable": "edge"},
    {"service": "Campaign Monitor", "cnames": ["createsend.com"],
     "fingerprints": ["Trying to access your account?",
                      "double check the spelling of the URL you were given"], "vulnerable": "edge"},
    {"service": "Intercom", "cnames": ["custom.intercom.help"],
     "fingerprints": ["This page is reserved for artistic dogs.",
                      "Uh oh. That page doesn't exist."], "vulnerable": "edge"},
]


def match_cname(cname: str) -> List[Dict]:
    """Return fingerprint entries whose CNAME pattern matches ``cname``.

    Matching is a case-insensitive substring test against the CNAME target, so a
    target like ``user.github.io`` matches the ``github.io`` pattern.
    """
    if not cname:
        return []
    target = cname.strip().lower().rstrip(".")
    return [fp for fp in FINGERPRINTS if any(pat in target for pat in fp["cnames"])]


def body_indicates_takeover(entry: Dict, body: str) -> bool:
    """True if the HTTP ``body`` contains any of the service's fingerprints."""
    if not body:
        return False
    return any(fp in body for fp in entry.get("fingerprints", []))
