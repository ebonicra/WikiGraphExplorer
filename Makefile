# commands
PY = python3
# makefile functions
define print_section
	@echo " "
	@echo "---------------$(1)----------------"
	@echo " "
endef

# targets
all: ex00 ex01 ex02 bonus

ex00:
	$(call print_section, ex00)
	$(PY) cache_wiki.py -p 'Erdős number'

ex01:
	$(call print_section, ex01)
	$(PY) cache_wiki.py -m 200
	$(PY) shortest_path.py 
	$(PY) shortest_path.py -v
	$(PY) shortest_path.py --from 'Python (programming language)' --to 'Welsh Corgi'
	$(PY) shortest_path.py --from 'Python (programming language)' --to 'Welsh Corgi' -v --non-directed

ex02:
	$(call print_section, ex02)
	$(PY) cache_wiki.py -m 30 -p 'Steve Jobs'
	$(PY) render_graph.py

bonus:
	$(call print_section, neo4j bonus)
	$(PY) cache_wiki.py -m 10 -n

clean:
	rm -f .env *.html *.png *.json

style:
	yapf -d --style pep8 *.py
format:
	yapf -i --style pep8 *.py

.PHONY: all style format