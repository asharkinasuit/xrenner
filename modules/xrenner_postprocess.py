from collections import defaultdict
from xrenner_classes import *
from xrenner_marker import markables_overlap
"""
xrenner - eXternally configurable REference and Non Named Entity Recognizer
Postprocessing module. Alters results of coreference analysis based on model settings,
such as deleting certain markables or re-wiring coreference relations according to a particular
annotation scheme
Author: Amir Zeldes and Shuo Zhang
"""


def postprocess_coref(markables, lex, markstart, markend, markbyhead):
	# Collect markable groups
	marks_by_group = defaultdict(list)
	for markable in markables:
		marks_by_group[markable.group].append(markable)

	# Order markables in each group to ensure backwards chain
	# except in the case of cataphors, which point forward
	for group in marks_by_group:
		last_mark = None
		for mark in marks_by_group[group]:
			if mark.coref_type != "cata":
				if last_mark is not None:
					mark.antecedent = last_mark
				last_mark = mark

	# Check for markables to remove in postprocessing
	if len(lex.filters["remove_head_func"].pattern) > 0:
		for mark in markables:
			if lex.filters["remove_head_func"].match(mark.head.func) is not None and (mark.form != "proper" or mark.text.strip() == "U.S."): # Proper restriction matches OntoNotes guidelines; US is interpreted as "American" (amod)
				splice_out(mark, marks_by_group[mark.group])
	if len(lex.filters["remove_child_func"].pattern) > 0:
		for mark in markables:
			for child_func in mark.head.child_funcs:
				if lex.filters["remove_child_func"].match(child_func) is not None:
					splice_out(mark, marks_by_group[mark.group])

	# Remove i in i rule (no overlapping markable coreference in group)
	# TODO: make this more efficient (iterates all pairwise comparisons)
	for group in marks_by_group:
		for mark1 in marks_by_group[group]:
			for mark2 in marks_by_group[group]:
				if not mark1 == mark2:
					if markables_overlap(mark1, mark2):
						if (mark1.end - mark1.start) > (mark2.end - mark2.start):
							splice_out(mark2, marks_by_group[group])
						else:
							splice_out(mark1, marks_by_group[group])

	# Remove cataphora if desired
	if lex.filters["remove_cataphora"]:
		for mark in markables:
			if mark.coref_type == "cata":
				mark.id = "0"
				if mark.antecedent != "none":
					mark.antecedent.id = "0"

	# Inactivate singletons if desired by setting their id to 0
	if lex.filters["remove_singletons"]:
		for group in marks_by_group:
			wipe_group = True
			if len(marks_by_group[group]) < 2:
				for singleton in marks_by_group[group]:
					singleton.id = "0"
			else:
				for singleton_candidate in marks_by_group[group]:
					if singleton_candidate.antecedent is not 'none':
						wipe_group = False
						break
				if wipe_group:
					for singleton in marks_by_group[group]:
						singleton.id = "0"


	# Add apposition envelopes if desired
	if lex.filters["add_appos_envelopes"]:
		for group in marks_by_group:
			for i in reversed(range(1,len(marks_by_group[group]))):
				# Print marks_by_group[group]
				mark = marks_by_group[group][i]
				prev = mark.antecedent
				if prev != "none":
					if prev.coref_type == "appos" and prev.antecedent != "none":
						# Two markables in the envelop: prev and prevprev
						prevprev = prev.antecedent
						envlop = create_envelope(prevprev,prev)
						markables.append(envlop)
						markstart[envlop.start].append(envlop)
						markend[envlop.end].append(envlop)

						# Markables_by_head
						head_id=str(prevprev.head.id) + "_" + str(prev.head.id)
						markbyhead[head_id] = envlop

						# Set some fields for the envlop markable
						envlop.non_antecdent_groups = prev.antecedent
						# New group number for the two markables inside the envelope
						ab_group = 1000 + int(prevprev.group) + int(prev.group)
						prevprev.group = ab_group
						prev.group = ab_group
						mark.antecedent = envlop
						prevprev.antecedent = "none"


def splice_out(mark, group):
	min_id = 0
	mark_id = int(mark.id.replace("referent_", ""))
	for member in group:
		if member.antecedent == mark:
			member.antecedent = mark.antecedent
		member_id = int(member.id.replace("referent_", ""))
		if (min_id == 0 or min_id > member_id) and member.id != mark.id:
			min_id = member_id
	mark.antecedent = "none"
	if str(mark_id) != mark.group:
		mark.group = str(mark_id)
	else:
		for member in group:
			if member != mark:
				member.group = str(min_id)
	mark.id = "0"


def create_envelope(first,second):
	mark_id="env"
	form = "proper" if (first.form == "proper" or second.form == "proper") else "common"
	head=first.head
	definiteness=first.definiteness
	start=first.start
	end=second.end
	text=first.text.strip() + " " + second.text.strip()
	entity=second.entity
	entity_certainty=second.entity_certainty
	subclass=first.subclass
	infstat=first.infstat
	agree=first.agree
	sentence=first.sentence
	antecedent=first.antecedent
	coref_type=first.coref_type
	group=first.group
	alt_entities=first.alt_entities
	alt_subclasses=first.alt_subclasses
	alt_agree=first.alt_agree

	envelope = Markable(mark_id, head, form, definiteness, start, end, text, entity, entity_certainty, subclass, infstat, agree, sentence, antecedent, coref_type, group, alt_entities, alt_subclasses, alt_agree)

	return envelope
