"""Request identity. Every data query filters on `principal.organization_id`.

`AUTH_MODE=demo` resolves each request to the seeded demo admin so the fixture-free app can
run locally; production refuses to start in demo mode (see config). Session auth is F15.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.errors import AppError
from app.config import get_settings
from app.domain.contracts import Role
from app.persistence import models as m
from app.persistence.db import get_session
from app.seed import DEMO_ADMIN_ID, DEMO_ORG_ID

DbSession = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class Principal:
    user_id: str
    organization_id: str
    role: Role

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


def get_principal(session: DbSession) -> Principal:
    if get_settings().auth_mode != "demo":
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    membership = session.get(m.Membership, (DEMO_ADMIN_ID, DEMO_ORG_ID))
    if membership is None:
        raise AppError(
            503,
            "demo_not_seeded",
            "The demo organization has not been seeded. Run `python -m app.cli seed-demo`.",
        )
    return Principal(membership.user_id, membership.organization_id, membership.role)


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
