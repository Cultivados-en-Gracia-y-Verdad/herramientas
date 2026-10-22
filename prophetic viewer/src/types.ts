export type ReviewStatus = 'unreviewed' | 'in_progress' | 'reviewed';
export type PredictiveStatus = 'undetermined' | 'predictive' | 'not_clearly_predictive';
export type FulfillmentStatus = 'not_assessed' | 'no_fulfillment_identified' | 'proposed_fulfillment' | 'textually_linked_fulfillment' | 'disputed' | 'undetermined';

export interface PassageListItem {
  id: number; original_reference: string; book: string | null; textual_review_status: ReviewStatus;
  predictive_statement_status: PredictiveStatus; fulfillment_assessment_status: FulfillmentStatus;
  updated_at: string; source_name: string; original_source_id: string; statement_count: number;
}
export interface Statement {
  id: number; description: string; explicitness: string; speaker: string | null; addressee: string | null;
  subject: string | null; predicted_action: string | null; temporal_expression: string | null;
  announcement_time: string | null; predicted_time: string | null; evidence_notes: string | null; review_status: string;
}
export interface History { id: number; field_name: string; previous_value: string; new_value: string; changed_at: string; evidence?: string; }
export interface PassageDetail extends PassageListItem {
  review_notes: string; passage_text: string | null; text_source: string | null; original_source_url: string | null;
  original_classification: string | null; original_fulfillment_claim: string | null; payne_mapping: string | null;
  imported_metadata: string; statements: Statement[]; history: History[];
}
