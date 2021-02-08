from .models import NERResult, NEREntitySpan
from typing import List

class NEREvaluator:
    def __init__(self, gold_entity_span_lists: List[List[NEREntitySpan]], pred_entity_span_lists: List[List[NEREntitySpan]]):
        """
        Constructor for NEREvaluator

        Parameters:
            gold_entity_span_lists (List[List[NEREntitySpan]]): List of gold entity spans lists for different documents.
            pred_entity_span_lists (List[List[NEREntitySpan]]): List of predicted entity span list for different documents.
        """
        if len(gold_entity_span_lists)!=len(pred_entity_span_lists):
            raise Exception(f'# of documents for which golden tags were provided {len(gold_entity_span_lists)}'
                            f'!= # of documents for which golden tags were provided {len(pred_entity_span_lists)}')
        
        self.gold_entity_span_lists = gold_entity_span_lists
        self.pred_entity_span_lists = pred_entity_span_lists

        # TODO: check for overlapping spans and throw exceptions

        self.unique_gold_tags = list(
            set([span.entity_type 
                    for gold_entity_span_list in gold_entity_span_lists 
                        for span in gold_entity_span_list]))

        self.results = NERResult()
        self.results_grouped_by_tags = {
            tag: NERResult() for tag in self.unique_gold_tags
        }

    def evaluate(self):
        pass


    def calculate_metrics_for_doc(self, gold_entity_spans: List[NEREntitySpan], pred_entity_spans: List[NEREntitySpan]):
        entity_span_sort_fn = lambda span: (span.start_idx, span.end_idx)

        # sort the entity list so we can make the evaluation faster (O(n)).
        gold_entity_spans.sort(key=entity_span_sort_fn)
        pred_entity_spans.sort(key=entity_span_sort_fn)

        # to check if the gold span or pred span was overlapping in last step
        gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False
        
        gold_idx, pred_idx = 0, 0
        results = NERResult()
        results_grouped_by_tags = {
            tag: NERResult() for tag in self.unique_gold_tags
        }

        while gold_idx<len(gold_entity_spans) and pred_idx<len(pred_entity_spans):
            if gold_entity_spans[gold_idx] == pred_entity_spans[pred_idx]:
                # Scenario I: Both entity type/labels and spans match perfectly 
                # TODO: collect data

                # it is safe to move cursor over
                # as overlapping spans are not allowed within the predicted entity spans list
                # and is also not allowed within gold entity span list
                gold_idx+=1
                pred_idx+=1
                
                gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False

            elif gold_entity_spans[gold_idx].spans_same_tokens_as(pred_entity_spans[pred_idx]):
                # Scenario IV: Wrong Entity types but, spans match perfectly 
                # TODO: collect data
                
                # it is safe to move cursor over
                # as overlapping spans are not allowed within the predicted entity spans list
                # and is also not allowed within gold entity span list
                gold_idx+=1
                pred_idx+=1
                
                gold_part_overlap_in_last_step, pred_part_overlap_in_last_step = False, False

            elif gold_entity_spans[gold_idx].overlaps_with(pred_entity_spans[pred_idx]):
                if gold_entity_spans[gold_idx].entity_type == pred_entity_spans[pred_idx].entity_type:
                    # Scenario V: Correct Entity Type, partial span overlap 
                    # TODO: collect data
                    pass
                else:
                    # Scenario VI: Wrong Entity Type, partial span overlap
                    # TODO: collect data
                    pass
            else:
                # Scenarion II or III
                pass
            




class NERTagListEvaluator(NEREvaluator):
    def __init__(self, tokens: List[List[str]], gold_tag_lists: List[List[str]], pred_tag_lists: List[List[str]]):
        """
            Constructor for tag list based evaluator

            Parameters:
                tokens (List[List[str]]): List of token lists for different documents.
                gold_tag_lists (List[List[str]]): List of golden tag lists for different documents.
                pred_tag_lists (List[List[str]]): List of predicted tag lists for different documents.
        """

        self.tokens = tokens
        self.gold_tag_lists = gold_tag_lists
        self.pred_tag_lists = pred_tag_lists

        gold_entity_spans = self.__tagged_list_to_span(
            self.gold_tag_lists)
        pred_entity_spans = self.__tagged_list_to_span(
            self.pred_tag_lists)

        super().__init__(gold_entity_spans, pred_entity_spans)

    def __tagged_list_to_span(self, tag_lists: List[List[str]]):
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

        for tag_list in tag_lists:
            labelled_entities = []
            for offset, token_tag in enumerate(tag_list):

                if token_tag == "O":
                    # if a sequence of non-"O" tags was seen last and
                    # a "O" tag is encountered => Label has ended.
                    if label is not None and start_offset is not None:
                        end_offset = offset - 1
                        labelled_entities.append(
                            NEREntitySpan(label, start_offset, end_offset)
                        )
                        start_offset = None
                        end_offset = None
                        label = None
                # if a non-"O" tag is encoutered => new label has started
                elif label is None:
                    label = token_tag[2:]
                    start_offset = offset
                # if another label begins => last labelled seq has ended
                elif label != token_tag[2:] or (
                    label == token_tag[2:] and token_tag[:1] == "B"
                ):

                    end_offset = offset - 1
                    labelled_entities.append(
                        NEREntitySpan(label, start_offset, end_offset)
                    )

                    # start of a new label
                    label = token_tag[2:]
                    start_offset = offset
                    end_offset = None

            if label is not None and start_offset is not None and end_offset is None:
                labelled_entities.append(
                    NEREntitySpan(label, start_offset, len(tag_list) - 1)
                )
            if len(labelled_entities) > 0:
                results.append(labelled_entities)
                labelled_entities = []

        return results
