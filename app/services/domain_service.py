"""Domain service — CRUD operations for life domains."""

from sqlalchemy.orm import Session

from app.models.domain import Domain
from app.schemas.domain import DomainCreate, DomainUpdate

DEFAULT_DOMAINS = [
    {"name": "Work", "color": "#B0C4DE", "sort_order": 0},
    {"name": "Personal", "color": "#C8B4A0", "sort_order": 1},
    {"name": "Health", "color": "#A8C8B0", "sort_order": 2},
    {"name": "Projects", "color": "#C0B0D0", "sort_order": 3},
    {"name": "Finance", "color": "#B8C4A8", "sort_order": 4},
    {"name": "Learning", "color": "#D4C8A0", "sort_order": 5},
    {"name": "Errands", "color": "#C0C0C0", "sort_order": 6},
]


class DomainService:
    def __init__(self, db: Session):
        self.db = db

    def list_domains(self, include_archived: bool = False) -> list[Domain]:
        query = self.db.query(Domain)
        if not include_archived:
            query = query.filter(Domain.is_archived == False)  # noqa: E712
        return query.order_by(Domain.sort_order).all()

    def get_domain(self, domain_id: int) -> Domain | None:
        return self.db.query(Domain).filter(Domain.id == domain_id).first()

    def create_domain(self, data: DomainCreate) -> Domain:
        domain = Domain(
            name=data.name,
            color=data.color,
            sort_order=data.sort_order,
        )
        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)
        return domain

    def update_domain(self, domain_id: int, data: DomainUpdate) -> Domain | None:
        domain = self.get_domain(domain_id)
        if not domain:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(domain, key, value)
        self.db.commit()
        self.db.refresh(domain)
        return domain

    def delete_domain(self, domain_id: int) -> bool:
        """Archive a domain (soft delete)."""
        domain = self.get_domain(domain_id)
        if not domain:
            return False
        domain.is_archived = True
        self.db.commit()
        return True

    def seed_defaults(self) -> list[Domain]:
        """Create default domains if none exist."""
        existing = self.db.query(Domain).count()
        if existing > 0:
            return self.list_domains()

        domains = []
        for d in DEFAULT_DOMAINS:
            domain = Domain(**d)
            self.db.add(domain)
            domains.append(domain)
        self.db.commit()
        for domain in domains:
            self.db.refresh(domain)
        return domains
