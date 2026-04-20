import os
import sys
from dotenv import load_dotenv

load_dotenv()

file_dir = os.getcwd()
src_dir = os.path.abspath(os.path.join(file_dir, ".."))
sys.path.append(src_dir)

# CDS API client
cdsapirc_path = os.getenv("CDS_API_RC_PATH", os.path.expanduser("~/.cdsapirc"))
sys.path.append(cdsapirc_path)
