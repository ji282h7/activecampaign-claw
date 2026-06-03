# Make targets:
#   make test                — run the full pytest suite
#   make lint                — ruff check scripts/ tests/
#   make verify              — test + lint (what CI runs)
#   make release VERSION=x   — bump SKILL.md + pyproject.toml + tag + push
#   make publish VERSION=x   — publish current state to clawhub
#
# The release target is intentionally minimal: it does NOT push commits or
# call publish. It bumps the version files, creates the commit + tag locally,
# and stops. You verify the diff, then run `git push --follow-tags` and
# `make publish VERSION=x`.

.PHONY: test lint verify release publish

test:
	python3 -m pytest

lint:
	python3 -m ruff check scripts/ tests/

verify: test lint

release:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make release VERSION=1.2.3"; exit 1; \
	fi
	@echo "Bumping to $(VERSION)..."
	@sed -i.bak -E 's/^version: .*/version: $(VERSION)/' SKILL.md && rm SKILL.md.bak
	@sed -i.bak -E 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml && rm pyproject.toml.bak
	@git add SKILL.md pyproject.toml CHANGELOG.md
	@git commit -m "$(VERSION)"
	@git tag -a "v$(VERSION)" -m "Release $(VERSION)"
	@echo ""
	@echo "Created commit + tag v$(VERSION). Review the diff, then:"
	@echo "  git push --follow-tags"
	@echo "  make publish VERSION=$(VERSION)"

publish:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make publish VERSION=1.2.3"; exit 1; \
	fi
	clawhub publish "$$(pwd)" \
		--version $(VERSION) \
		--slug activecampaign-claw \
		--name "ActiveCampaign (50+ Capabilities)" \
		--changelog "See CHANGELOG.md for the full entry."
