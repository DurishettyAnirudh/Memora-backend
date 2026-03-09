"""Unit tests for DomainService."""

import pytest

from app.models.domain import Domain
from app.schemas.domain import DomainCreate, DomainUpdate
from app.services.domain_service import DomainService, DEFAULT_DOMAINS


@pytest.fixture()
def domain_service(db):
    return DomainService(db)


class TestSeedDefaults:
    def test_seeds_default_domains(self, domain_service):
        domains = domain_service.seed_defaults()
        assert len(domains) == len(DEFAULT_DOMAINS)
        names = {d.name for d in domains}
        assert "Work" in names
        assert "Personal" in names
        assert "Health" in names

    def test_does_not_reseed(self, domain_service, db):
        domain_service.seed_defaults()
        # Seed again — should return existing, not create more
        domains = domain_service.seed_defaults()
        assert len(domains) == len(DEFAULT_DOMAINS)
        assert db.query(Domain).count() == len(DEFAULT_DOMAINS)


class TestCRUD:
    def test_create_domain(self, domain_service):
        created = domain_service.create_domain(
            DomainCreate(name="Custom", color="#FF0000", sort_order=10)
        )
        assert created.id is not None
        assert created.name == "Custom"

    def test_list_domains_excludes_archived(self, domain_service):
        domain_service.create_domain(DomainCreate(name="Active", color="#000", sort_order=0))
        d = domain_service.create_domain(DomainCreate(name="Archived", color="#111", sort_order=1))
        domain_service.delete_domain(d.id)  # archive
        active = domain_service.list_domains(include_archived=False)
        names = [d.name for d in active]
        assert "Active" in names
        assert "Archived" not in names

    def test_list_domains_includes_archived(self, domain_service):
        domain_service.create_domain(DomainCreate(name="Active", color="#000", sort_order=0))
        d = domain_service.create_domain(DomainCreate(name="Archived", color="#111", sort_order=1))
        domain_service.delete_domain(d.id)
        all_domains = domain_service.list_domains(include_archived=True)
        names = [d.name for d in all_domains]
        assert "Archived" in names

    def test_update_domain(self, domain_service):
        d = domain_service.create_domain(DomainCreate(name="Old", color="#000", sort_order=0))
        updated = domain_service.update_domain(d.id, DomainUpdate(name="New", color="#FFF"))
        assert updated.name == "New"
        assert updated.color == "#FFF"

    def test_update_nonexistent(self, domain_service):
        assert domain_service.update_domain(99999, DomainUpdate(name="X")) is None

    def test_delete_archives(self, domain_service):
        d = domain_service.create_domain(DomainCreate(name="ToDelete", color="#000", sort_order=0))
        assert domain_service.delete_domain(d.id) is True
        fetched = domain_service.get_domain(d.id)
        assert fetched.is_archived is True

    def test_delete_nonexistent(self, domain_service):
        assert domain_service.delete_domain(99999) is False
