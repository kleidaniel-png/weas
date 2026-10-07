from fastapi import APIRouter, Depends

from ..backup import list_backups, run_backup
from ..config import BACKUP_DIR
from ..models import User
from ..security import require

router = APIRouter(prefix="/api/backup", tags=["Datensicherung"])
manage = require("settings.manage")


def _info() -> dict:
    return {"directory": str(BACKUP_DIR), "backups": list_backups()}


@router.get("")
def backups(_: User = Depends(manage)):
    return _info()


@router.post("")
def backup_now(_: User = Depends(manage)):
    run_backup()
    return _info()
