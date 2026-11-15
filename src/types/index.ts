export type Language = 'en' | 'hi' | 'kn' | 'te';

export interface LanguageInfo {
  code: Language;
  name: string;
  nativeName: string;
  subtext: string;
  flagText: string;
}

export type SchemeCategory = 
  | 'all' 
  | 'agriculture' 
  | 'healthcare' 
  | 'housing' 
  | 'social_welfare' 
  | 'employment' 
  | 'education'
  | 'women_and_child'
  | 'energy';

export type EligibilityStatus = 'eligible' | 'possibly_eligible' | 'not_eligible';

export interface SchemeDocument {
  id: string;
  name: string;
  required: boolean;
  description: string;
}

export interface Scheme {
  id: string;
  name: string;
  nativeName: string;
  ministry: string;
  category: SchemeCategory;
  benefit: string;
  benefitHighlight: string;
  status: EligibilityStatus;
  matchScore: number;
  description: string;
  matchingCriteria: string[];
  missingCriteria?: string[];
  failedCriteria?: string[];
  criteriaList: string[];
  exclusions: string[];
  requiredDocuments: SchemeDocument[];
  applicationSteps: string[];
  officialUrl: string;
  portalName: string;
  cscApplicable: boolean;
  lastUpdated: string;
  verifiedOfficial: boolean;
  stateApplicability?: string[];
}

export type AttributeSource = 'user' | 'detected';

export type AttributeSourcesMap = Partial<Record<keyof UserProfile, AttributeSource>>;

export interface UserProfile {
  age?: number;
  state?: string;
  district?: string;
  gender?: string;
  occupation?: string;
  occupationDetail?: string;
  ownsAgriculturalLand?: boolean;
  landholdingHectares?: number;
  landholding?: string;
  annualIncome?: number;
  socialCategory?: string;
  hasBPLCard?: boolean;
  hasBplCard?: boolean;
  isDifferentlyAbled?: boolean;
  farmerType?: string;
  isBankDefaulter?: boolean;
  isTenantFarmer?: boolean;
  isAlliedActivityWorker?: boolean;
  isStreetVendor?: boolean;
  isUnorganisedWorker?: boolean;
  incomeRange?: string;
  paysIncomeTax?: boolean;
  hasRegularGovtJob?: boolean;
  monthlyPension?: number;
  ownsPuccaHouse?: boolean;
  isPregnantOrLactating?: boolean;
  hasSavingsAccount?: boolean;
  hasBankPassbook?: boolean;
}

export interface ProvenanceCitationItem {
  chunk_id: string;
  scheme_id: string;
  category: string;
  document_title: string;
  issuing_authority: string;
  source_url: string;
  relevant_section?: string;
  page_ref?: string;
  verification_status: string;
  status_disclosure: string;
  attribution_label: string;
}

export type CanonicalEligibilityStatus =
  | 'ELIGIBLE'
  | 'NOT_ELIGIBLE'
  | 'NEEDS_MORE_INFORMATION'
  | 'NOT_VERIFIED';

export interface EligibilityOutcomeItem {
  scheme_id: string;
  scheme_name: Record<string, string>;
  status: CanonicalEligibilityStatus | 'POSSIBLY_ELIGIBLE';
  summary: string;
  satisfied_conditions?: string[];
  failed_conditions?: string[];
  missing_prompts?: string[];
  unresolved_notes?: string[];
  is_clarification_needed?: boolean;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  isVoiceInput?: boolean;
  transcriptionConfidence?: number;
  suggestedSchemeIds?: string[];
  attributesFound?: { label: string; value: string }[];
  citations?: ProvenanceCitationItem[];
  formattedCitationsMarkdown?: string;
  eligibilityResult?: EligibilityOutcomeItem;
  suggestedFollowups?: string[];
  intent?: string;
}

export interface SavedSchemeItem {
  schemeId: string;
  savedAt: string;
  checkedDocumentIds: string[];
  notes?: string;
}

