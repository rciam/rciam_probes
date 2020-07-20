PKGNAME=rciam_probes
PKGVERSION=$(shell grep -s '^__version__\s*=' setup.py | sed -e 's/^__version__\s*=\s*//')
.PHONY : clean

dist:
	@echo "-- python build dist --"
	@python3 setup.py sdist
	@ls -l dist
	@mv dist/${PKGNAME}-${PKGVERSION}.tar.gz .
	@rm -r dist

srpm: dist
	@echo "-- Building srpm --"
	@rpmbuild -ts --define='dist.el6' ${PKGNAME}-${PKGVERSION}.tar.gz

rpm: dist
	@echo "-- Building rpm --"
	@rpmbuild -ta ${PKGNAME}-${PKGVERSION}.tar.gz

sources: dist

clean:
	@echo "-- Cleaning --"
	@rm -rf dist
	@rm -rf ${PKGNAME}-${PKGVERSION}.tar.gz
	@find . -name '${PKGNAME}.egg-info' -exec rm -fr {} +
	@find . -name '${PKGNAME}.egg' -exec rm -f {} +
