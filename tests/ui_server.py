"""Synthetic panel transport ONLY for UI QA. Never part of the production launcher."""
import argparse
from pathlib import Path
import httpx
import uvicorn
from app.main import create_app
from app.settings import Settings
from .conftest import Panel
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--port',type=int,required=True);args=p.parse_args()
app=create_app(Settings(data_dir=Path(args.data),allowed_hosts=('panel.example',),worker_enabled=True,test_network=True),httpx.MockTransport(Panel()))
uvicorn.run(app,host='127.0.0.1',port=args.port,log_config=None,access_log=False)
