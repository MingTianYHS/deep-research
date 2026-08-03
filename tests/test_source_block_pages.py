from pathlib import Path
import sys
SCRIPT_DIR=Path(__file__).parents[1]/".agents/skills/deep-research/scripts";sys.path.insert(0,str(SCRIPT_DIR))
from lib.source_attempts import assess_response


def test_access_challenges_login_and_soft_404_are_not_evidence():
    pages=["<title>Just a moment...</title>Enable JavaScript and cookies to continue","<title>Sign in</title><form>Password</form>","<title>Page not found</title>The page you requested does not exist.","<title>Verify you are human</title>Captcha"]
    for page in pages:
        result=assess_response(200,page);assert not result["eligible_for_evidence"] and result["status"]=="unavailable"

def test_normal_content_remains_eligible():
    result=assess_response(200,"<title>Official report</title><main>Substantive published findings.</main>");assert result["eligible_for_evidence"] and len(result["content_sha256"])==64
