from .models import ResultAggregator, Span
from collections import defaultdict
from typing import List, Tuple


class NEREvaluator:
    def __init__(self, gold_entity_span_lists: List[List[Span]], pred_entity_span_lists: List[List[Span]]):
        """
        Constructor for NEREvaluator

        Args:
            gold_entity_span_lists (List[List[Span]]): List of gold entity spans lists for different documents.
            pred_entity_span_lists (List[List[Span]]): List of predicted entity span list for different documents.
        """
        if len(gold_entity_span_lists) != len(pred_entity_span_lists):
            raise Exception(f'# of documents for which golden tags were provided {len(gold_entity_span_lists)}'
                            f'!= # of documents for which golden tags were provided {len(pred_entity_span_lists)}')

        self.gold_entity_span_lists = gold_entity_span_lists
        self.pred_entity_span_lists = pred_entity_span_lists

        # TODO: check for overlapping spans and throw exceptions

        self.unique_gold_tags = list(
            set([span.span_type
                 for gold_entity_span_list in gold_entity_span_lists
                 for span in gold_entity_span_list]))

        self.results = ResultAggregator()
        self.results_grouped_by_tags = defaultdict(
            lambda: ResultAggregator())

    def evaluate(self) -> Tuple[ResultAggregator, ResultAggregator]:
        """Runs the evaluation and return results

        Returns:
            Tuple[ResultAggregator, ResultAggregator]: (Results, Results Grouped by tags)
        """
        results_by_doc = []
        results = ResultAggregator()

        for gold_spans, pred_spans in zip(self.gold_entity_span_lists, self.pred_entity_span_lists):
            results_for_curr_doc = self.__calculate_metrics_for_doc(
                gold_spans, pred_spans)
            results_by_doc.append(results_for_curr_doc)
            results.append_result_aggregator(results_for_curr_doc[0])

        return results, results_for_curr_doc

    def __calculate_metrics_for_doc(self, gold_entity_spans: List[Span], pred_entity_spans: List[Span]) -> Tuple[ResultAggregator, ResultAggregator]:
        """Calculate the metrics for a particular document.

        Args:
            gold_entity_spans (List[Span]): list of gold entity spans
            pred_entity_spans (List[Span]): list of predicted entity spans

        Returns:
            Tuple[ResultAggregator, ResultAggregator]: (Results, Results Grouped by tags)
        """

        def entity_span_sort_fn(span): return (span.start_idx, span.end_idx)

        # sort the entity list so we can make the evaluation faster (O(n)).
        gold_entity_spans.sort(key=entity_span_sort_fn)
        pred_entity_spans.sort(key=entity_span_sort_fn)

        # to check if the gold span or pred span was overlapping in last step
        gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False

        gold_idx, pred_idx = 0, 0
        results = ResultAggregator()
        results_grouped_by_tags = defaultdict(lambda: ResultAggregator())

        while gold_idx < len(gold_entity_spans) and pred_idx < len(pred_entity_spans):
            if gold_entity_spans[gold_idx] == pred_entity_spans[pred_idx]:
                # Scenario I: Both entity type/labels and spans match perfectly
                results.add_type_match_bounds_match(
                    gold_entity_spans[gold_idx], pred_entity_spans[pred_idx])

                gold_span_type = gold_entity_spans[gold_idx].span_type
                results_grouped_by_tags[gold_span_type].add_type_match_bounds_match(
                    gold_entity_spans[gold_idx],
                    pred_entity_spans[pred_idx]
                )

                # it is safe to move cursor over
                # as overlapping spans are not allowed within the predicted entity spans list
                # and is also not allowed within gold entity span list
                gold_idx += 1
                pred_idx += 1

                gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False

            elif gold_entity_spans[gold_idx].bounds_same_tokens_as(pred_entity_spans[pred_idx]):
                # Scenario IV: Wrong Entity types but, spans match perfectly
                results.add_type_mismatch_bounds_match(
                    gold_entity_spans[gold_idx], pred_entity_spans[pred_idx])

                gold_span_type = gold_entity_spans[gold_idx].span_type
                results_grouped_by_tags[gold_span_type].add_type_mismatch_bounds_match(
                    gold_entity_spans[gold_idx],
                    pred_entity_spans[pred_idx]
                )

                # it is safe to move cursor over
                # as overlapping spans are not allowed within the predicted entity spans list
                # and is also not allowed within gold entity span list
                gold_idx += 1
                pred_idx += 1

                gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False

            elif gold_entity_spans[gold_idx].overlaps_with(pred_entity_spans[pred_idx]):
                if gold_entity_spans[gold_idx].span_type == pred_entity_spans[pred_idx].span_type:
                    # Scenario V: Correct Entity Type, partial span overlap
                    results.add_type_match_bounds_partial(
                        gold_entity_spans[gold_idx],
                        pred_entity_spans[pred_idx]
                    )

                    gold_span_type = gold_entity_spans[gold_idx].span_type
                    results_grouped_by_tags[gold_span_type].add_type_match_bounds_partial(
                        gold_entity_spans[gold_idx],
                        pred_entity_spans[pred_idx]
                    )
                else:
                    # Scenario VI: Wrong Entity Type, partial span overlap
                    results.add_type_mismatch_bounds_partial(
                        gold_entity_spans[gold_idx],
                        pred_entity_spans[pred_idx]
                    )

                    gold_span_type = gold_entity_spans[gold_idx].span_type
                    results_grouped_by_tags[gold_span_type].add_type_mismatch_bounds_partial(
                        gold_entity_spans[gold_idx],
                        pred_entity_spans[pred_idx]
                    )

                if pred_entity_spans[pred_idx].end_idx > gold_entity_spans[gold_idx].end_idx:
                    pred_part_overlap_in_last_step = True
                    gold_idx += 1
                elif pred_entity_spans[pred_idx].end_idx < gold_entity_spans[gold_idx].end_idx:
                    gold_part_overlap_in_last_step = True
                    pred_idx += 1
                else:
                    gold_idx += 1
                    pred_idx += 1
                    gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False

            else:
                if pred_entity_spans[pred_idx].start_idx > gold_entity_spans[gold_idx].end_idx:
                    if not gold_part_overlap_in_last_step:
                        # Scenario III system missed an entity
                        results.add_missed_gold_span(
                            gold_entity_spans[gold_idx])

                        gold_span_type = gold_entity_spans[gold_idx].span_type
                        results_grouped_by_tags[gold_span_type].add_missed_gold_span(
                            gold_entity_spans[gold_idx]
                        )

                    gold_idx += 1
                    gold_part_overlap_in_last_step = False
                elif pred_entity_spans[pred_idx].end_idx < gold_entity_spans[gold_idx].start_idx:
                    if not pred_part_overlap_in_last_step:
                        # Scenario II system hypothesised an extra entity
                        results.add_unecessary_predicted_span(
                            pred_entity_spans[pred_idx])

                        pred_span_type = pred_entity_spans[pred_idx].span_type
                        results_grouped_by_tags[pred_span_type].add_unecessary_predicted_span(
                            pred_entity_spans[pred_idx]
                        )

                    pred_idx += 1
                    pred_part_overlap_in_last_step = True

        if gold_part_overlap_in_last_step:
            gold_idx += 1

        while gold_idx < len(gold_entity_spans):
            # Scenario III: missed entity
            results.add_missed_gold_span(
                gold_entity_spans[gold_idx])

            gold_span_type = gold_entity_spans[gold_idx].span_type
            results_grouped_by_tags[gold_span_type].add_missed_gold_span(
                gold_entity_spans[gold_idx]
            )

            gold_idx += 1

        if pred_part_overlap_in_last_step:
            pred_idx += 1
        while pred_idx < len(pred_entity_spans):
            # Scenario II: hypothesised entity incorrect
            results.add_unecessary_predicted_span(
                pred_entity_spans[pred_idx])

            pred_span_type = pred_entity_spans[pred_idx].span_type
            results_grouped_by_tags[pred_span_type].add_unecessary_predicted_span(
                pred_entity_spans[pred_idx]
            )

            pred_idx += 1

        return results, results_grouped_by_tags


class NERTagListEvaluator(NEREvaluator):
    def __init__(self, tokens: List[List[str]], gold_tag_lists: List[List[str]], pred_tag_lists: List[List[str]], entity_context_padding=0):
        """Constructor for tag list based evaluator

        Args:
            tokens (List[List[str]]): List of token lists for different documents.
            gold_tag_lists (List[List[str]]): List of golden tag lists for different documents.
            pred_tag_lists (List[List[str]]): List of predicted tag lists for different documents.
        """
        # TODO: Check for nesting and convert nested items to list
        self.tokens = list(tokens)
        self.gold_tag_lists = list(gold_tag_lists)
        self.pred_tag_lists = list(pred_tag_lists)
        self.entity_context_padding = entity_context_padding

        gold_entity_spans = self.__tagged_list_to_span(
            self.gold_tag_lists, self.tokens)
        pred_entity_spans = self.__tagged_list_to_span(
            self.pred_tag_lists, self.tokens)

        super().__init__(gold_entity_spans, pred_entity_spans)

    def __tagged_list_to_span(self, tag_lists: List[List[str]], token_lists: List[List[str]]):
        """
            Create a list of tagged entities with span offsets.

            Parameters:
                tag_list (List[List[str]]): List of tag lists for different documents
            Returns:
                List of entity span lists for each document.
        """
        results = []
        start_offset = None
        end_offset = None
        label = None
        valid_token_tag_prefix = ('B', 'I', 'L', 'O', 'U')

        def get_context_tokens(token_list, start_offset, end_offset): return (
            token_list[max(0, start_offset-self.entity_context_padding):
                        min(end_offset+self.entity_context_padding+1, len(token_list))]
        )

        if len(tag_lists) != len(token_lists):
            raise Exception(
                'Exception: Number of tags lists and tokens lists are not the same.')

        for tag_list, token_list in zip(tag_lists, token_lists):
            # reset everything
            labelled_entities = []

            start_offset = None
            end_offset = None
            label = None

            if len(tag_list) != len(token_list):
                raise Exception(
                    f'Exception: Number of tags and tokens are not the same.'
                    f'Tag List:{tag_list} Token List: {token_list}'
                )

            for offset, (token_tag, _) in enumerate(zip(tag_list, token_list)):
                if token_tag == "O":
                    # if a sequence of non-"O" tags was seen last and
                    # a "O" tag is encountered => Label has ended.
                    if label is not None and start_offset is not None:
                        end_offset = offset - 1
                        labelled_entities.append(
                            Span(label, start_offset,
                                          end_offset, token_list[start_offset:end_offset+1], 
                                          get_context_tokens(token_list, start_offset, end_offset))
                        )
                        start_offset = None
                        end_offset = None
                        label = None
                # if a non-"O" tag is encoutered => new label has started
                elif label is None and token_tag.startswith(valid_token_tag_prefix):
                    label = token_tag[2:]
                    start_offset = offset
                # if another label begins => last labelled seq has ended
                elif (label != token_tag[2:] and token_tag.startswith(valid_token_tag_prefix)) or (
                    label == token_tag[2:] and (
                        token_tag[:1] == "B" or token_tag[:1] == "U")
                ):

                    end_offset = offset - 1
                    labelled_entities.append(
                        Span(label, start_offset,
                                      end_offset, token_list[start_offset:end_offset+1], 
                                      get_context_tokens(token_list, start_offset, end_offset))
                    )

                    # start of a new label
                    label = token_tag[2:]
                    start_offset = offset
                    end_offset = None
                elif not token_tag.startswith(valid_token_tag_prefix):
                    # TODO: Add line information
                    raise Exception(f'Unknown Token Tag: {token_tag}')

            if label is not None and start_offset is not None and end_offset is None:
                end_offset = len(tag_list) - 1
                labelled_entities.append(
                    Span(label, start_offset, end_offset, token_list[start_offset:end_offset+1], 
                    get_context_tokens(token_list, start_offset, end_offset))
                )

            if len(labelled_entities) > 0:
                results.append(labelled_entities)
                labelled_entities = []

        return results
