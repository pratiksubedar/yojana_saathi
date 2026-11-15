import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  CheckCircle2,
  Edit3,
  ShieldCheck,
  ArrowRight,
  Save,
  X,
  Sparkles,
  Trash2,
  MapPin,
  Globe,
  HelpCircle,
  AlertCircle,
  Check,
  Mic,
  Coins,
  FileText,
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { useApp } from '../context/AppContext';
import { LANGUAGES, t } from '../data/translations';
import { UserProfile, Language } from '../types';
import { sendChatMessage, getSessionId } from '../services/chatApi';
import { evaluateEligibility, mapUserProfileToCitizenAttributes, fetchSchemes } from '../services/schemeApi';

export const INDIAN_STATES_AND_UTS: { code: string; name: string }[] = [
  { code: 'AN', name: 'Andaman and Nicobar Islands' },
  { code: 'AP', name: 'Andhra Pradesh' },
  { code: 'AR', name: 'Arunachal Pradesh' },
  { code: 'AS', name: 'Assam' },
  { code: 'BR', name: 'Bihar' },
  { code: 'CH', name: 'Chandigarh' },
  { code: 'CG', name: 'Chhattisgarh' },
  { code: 'DN', name: 'Dadra and Nagar Haveli and Daman and Diu' },
  { code: 'DL', name: 'Delhi' },
  { code: 'GA', name: 'Goa' },
  { code: 'GJ', name: 'Gujarat' },
  { code: 'HR', name: 'Haryana' },
  { code: 'HP', name: 'Himachal Pradesh' },
  { code: 'JK', name: 'Jammu and Kashmir' },
  { code: 'JH', name: 'Jharkhand' },
  { code: 'KA', name: 'Karnataka' },
  { code: 'KL', name: 'Kerala' },
  { code: 'LA', name: 'Ladakh' },
  { code: 'LD', name: 'Lakshadweep' },
  { code: 'MP', name: 'Madhya Pradesh' },
  { code: 'MH', name: 'Maharashtra' },
  { code: 'MN', name: 'Manipur' },
  { code: 'ML', name: 'Meghalaya' },
  { code: 'MZ', name: 'Mizoram' },
  { code: 'NL', name: 'Nagaland' },
  { code: 'OD', name: 'Odisha' },
  { code: 'PY', name: 'Puducherry' },
  { code: 'PB', name: 'Punjab' },
  { code: 'RJ', name: 'Rajasthan' },
  { code: 'SK', name: 'Sikkim' },
  { code: 'TN', name: 'Tamil Nadu' },
  { code: 'TS', name: 'Telangana' },
  { code: 'TR', name: 'Tripura' },
  { code: 'UP', name: 'Uttar Pradesh' },
  { code: 'UK', name: 'Uttarakhand' },
  { code: 'WB', name: 'West Bengal' },
];

export const OCCUPATION_OPTIONS = [
  'Farmer',
  'Agricultural Labourer',
  'Student',
  'Salaried Employee',
  'Self-Employed',
  'Business Owner',
  'Unemployed',
  'Homemaker',
  'Pensioner',
  'Street Vendor',
  'Other',
];

export const FARMER_TYPES_LIST = [
  'Landowner',
  'Tenant Farmer',
  'Sharecropper',
  'Animal Husbandry / Fisheries',
  'Other Allied',
];

export const CASTE_CATEGORIES = ['General', 'OBC', 'SC', 'ST', 'EWS'];
export const GENDER_OPTIONS = ['Female', 'Male', 'Other'];

export const LOCALIZED_OCCUPATION_MAP: Record<Language, { key: string; label: string }[]> = {
  en: [
    { key: 'Farmer', label: 'Farmer' },
    { key: 'Agricultural Labourer', label: 'Agricultural Labourer' },
    { key: 'Student', label: 'Student' },
    { key: 'Salaried Employee', label: 'Salaried Employee' },
    { key: 'Self-Employed', label: 'Self-Employed' },
    { key: 'Business Owner', label: 'Business Owner' },
    { key: 'Unemployed', label: 'Unemployed' },
    { key: 'Homemaker', label: 'Homemaker' },
    { key: 'Pensioner', label: 'Pensioner' },
    { key: 'Street Vendor', label: 'Street Vendor' },
    { key: 'Other', label: 'Other' },
  ],
  hi: [
    { key: 'Farmer', label: 'किसान (Farmer)' },
    { key: 'Agricultural Labourer', label: 'कृषि मजदूर' },
    { key: 'Student', label: 'छात्र (Student)' },
    { key: 'Salaried Employee', label: 'वेतनभोगी कर्मचारी' },
    { key: 'Self-Employed', label: 'स्वरोजगार' },
    { key: 'Business Owner', label: 'व्यापारी / दुकान मालिक' },
    { key: 'Unemployed', label: 'बेरोजगार' },
    { key: 'Homemaker', label: 'गृहिणी (Homemaker)' },
    { key: 'Pensioner', label: 'पेंशनभोगी' },
    { key: 'Street Vendor', label: 'रेहड़ी-पटरी वेंडर (Street Vendor)' },
    { key: 'Other', label: 'अन्य' },
  ],
  kn: [
    { key: 'Farmer', label: 'ರೈತ (Farmer)' },
    { key: 'Agricultural Labourer', label: 'ಕೃಷಿ ಕಾರ್ಮಿಕ' },
    { key: 'Student', label: 'ವಿದ್ಯಾರ್ಥಿ (Student)' },
    { key: 'Salaried Employee', label: 'ವೇತನ ಪಡೆಯುವ ನೌಕರ' },
    { key: 'Self-Employed', label: 'ಸ್ವಯಂ ಉದ್ಯೋಗಿ' },
    { key: 'Business Owner', label: 'ವ್ಯಾಪಾರಿ / ಅಂಗಡಿ ಮಾಲೀಕ' },
    { key: 'Unemployed', label: 'ನಿರುದ್ಯೋಗಿ' },
    { key: 'Homemaker', label: 'ಗೃಹಿಣಿ (Homemaker)' },
    { key: 'Pensioner', label: 'ಪಿಂಚಣಿದಾರ' },
    { key: 'Street Vendor', label: 'ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿ (Street Vendor)' },
    { key: 'Other', label: 'ಇತರೆ' },
  ],
  te: [
    { key: 'Farmer', label: 'రైతు (Farmer)' },
    { key: 'Agricultural Labourer', label: 'వ్యవసాయ కూలీ' },
    { key: 'Student', label: 'విద్యార్థి (Student)' },
    { key: 'Salaried Employee', label: 'జీతం పొందే ఉద్యోగి' },
    { key: 'Self-Employed', label: 'స్వయం ఉపాధి' },
    { key: 'Business Owner', label: 'వ్యాపారి / దుకాణం యజమాని' },
    { key: 'Unemployed', label: 'నిరుద్యోగి' },
    { key: 'Homemaker', label: 'గృహిణి (Homemaker)' },
    { key: 'Pensioner', label: 'పెన్షనర్' },
    { key: 'Street Vendor', label: 'వీధి వ్యాపారి (Street Vendor)' },
    { key: 'Other', label: 'ఇతర' },
  ],
};

export const LOCALIZED_FARMER_TYPES_MAP: Record<Language, { key: string; label: string }[]> = {
  en: [
    { key: 'Landowner', label: 'Landowner' },
    { key: 'Tenant Farmer', label: 'Tenant Farmer' },
    { key: 'Sharecropper', label: 'Sharecropper' },
    { key: 'Animal Husbandry / Fisheries', label: 'Animal Husbandry / Fisheries' },
    { key: 'Other Allied', label: 'Other Allied' },
  ],
  hi: [
    { key: 'Landowner', label: 'भूमि मालिक (Landowner)' },
    { key: 'Tenant Farmer', label: 'पट्टेदार / किरायेदार किसान (Tenant)' },
    { key: 'Sharecropper', label: 'बटाईदार किसान (Sharecropper)' },
    { key: 'Animal Husbandry / Fisheries', label: 'पशुपालन / मत्स्य पालन' },
    { key: 'Other Allied', label: 'अन्य संबद्ध कृषि कार्य' },
  ],
  kn: [
    { key: 'Landowner', label: 'ಭೂಮಾಲೀಕ (Landowner)' },
    { key: 'Tenant Farmer', label: 'ಗೇಣಿದಾರ ರೈತ (Tenant)' },
    { key: 'Sharecropper', label: 'ಪಾಲುದಾರ ರೈತ (Sharecropper)' },
    { key: 'Animal Husbandry / Fisheries', label: 'ಪಶುಸಂಗೋಪನೆ / ಮೀನುಗಾರಿಕೆ' },
    { key: 'Other Allied', label: 'ಇತರ ಕೃಷಿ ಪೂರಕ ಚಟುವಟಿಕೆಗಳು' },
  ],
  te: [
    { key: 'Landowner', label: 'భూ యజమాని (Landowner)' },
    { key: 'Tenant Farmer', label: 'కౌలు రైతు (Tenant)' },
    { key: 'Sharecropper', label: 'వాటా రైతు (Sharecropper)' },
    { key: 'Animal Husbandry / Fisheries', label: 'పశుసంవర్ధక / మత్స్య రంగం' },
    { key: 'Other Allied', label: 'ఇతర అనుబంధ వ్యవసాయ పనులు' },
  ],
};

export const LOCALIZED_GENDERS_MAP: Record<Language, { key: string; label: string }[]> = {
  en: [
    { key: 'Female', label: 'Female' },
    { key: 'Male', label: 'Male' },
    { key: 'Other', label: 'Other' },
  ],
  hi: [
    { key: 'Female', label: 'महिला (Female)' },
    { key: 'Male', label: 'पुरुष (Male)' },
    { key: 'Other', label: 'अन्य (Other)' },
  ],
  kn: [
    { key: 'Female', label: 'ಮಹಿಳೆ (Female)' },
    { key: 'Male', label: 'ಪುರುಷ (Male)' },
    { key: 'Other', label: 'ಇತರೆ (Other)' },
  ],
  te: [
    { key: 'Female', label: 'మహిళ (Female)' },
    { key: 'Male', label: 'పురుషుడు (Male)' },
    { key: 'Other', label: 'ఇతరులు (Other)' },
  ],
};

export const LOCALIZED_CASTES_MAP: Record<Language, { key: string; label: string }[]> = {
  en: [
    { key: 'General', label: 'General / Open' },
    { key: 'OBC', label: 'OBC (Other Backward Classes)' },
    { key: 'SC', label: 'SC (Scheduled Caste)' },
    { key: 'ST', label: 'ST (Scheduled Tribe)' },
    { key: 'EWS', label: 'EWS (Economically Weaker Section)' },
  ],
  hi: [
    { key: 'General', label: 'सामान्य (General)' },
    { key: 'OBC', label: 'अन्य पिछड़ा वर्ग (OBC)' },
    { key: 'SC', label: 'अनुसूचित जाति (SC)' },
    { key: 'ST', label: 'अनुसूचित जनजाति (ST)' },
    { key: 'EWS', label: 'आर्थिक रूप से कमजोर (EWS)' },
  ],
  kn: [
    { key: 'General', label: 'ಸಾಮಾನ್ಯ (General)' },
    { key: 'OBC', label: 'ಇತರೆ ಹಿಂದುಳಿದ ವರ್ಗ (OBC)' },
    { key: 'SC', label: 'ಪರಿಶಿಷ್ಟ ಜಾತಿ (SC)' },
    { key: 'ST', label: 'ಪರಿಶಿಷ್ಟ ಪಂಗಡ (ST)' },
    { key: 'EWS', label: 'ಆರ್ಥಿಕವಾಗಿ ದುರ್ಬಲ ವರ್ಗ (EWS)' },
  ],
  te: [
    { key: 'General', label: 'జనరల్ (General)' },
    { key: 'OBC', label: 'ఇతర వెనుకబడిన తరగతులు (OBC)' },
    { key: 'SC', label: 'షెడ్యూల్డ్ కులాలు (SC)' },
    { key: 'ST', label: 'షెడ్యూల్డ్ తెగలు (ST)' },
    { key: 'EWS', label: 'ఆర్థికంగా బలహీన వర్గాలు (EWS)' },
  ],
};

export const LOCALIZED_ATTRIBUTE_CARDS: Record<
  Language,
  Partial<Record<keyof UserProfile, { label: string; desc: string }>>
> = {
  en: {
    age: { label: 'Age', desc: 'Used for age-targeted schemes and pensions' },
    gender: { label: 'Gender', desc: 'Required for women-targeted welfare and maternity grants' },
    state: { label: 'State / UT', desc: 'Filters state-level eligibility and regional quotas' },
    occupation: { label: 'Occupation', desc: 'Identifies farmer, street vendor, and worker benefits' },
    farmerType: { label: 'Farmer / Cultivator Category', desc: 'Owner cultivator, tenant farmer, or allied sector worker' },
    annualIncome: { label: 'Annual Household Income', desc: 'Required for income caps on subsidies and housing grants' },
    paysIncomeTax: { label: 'Income Tax Payer', desc: 'Exclusion criterion for PM-KISAN, PM-KMY, and direct welfare' },
    hasRegularGovtJob: { label: 'Regular Govt / PSU Job', desc: 'Government employees and their families are excluded from cash transfers' },
    monthlyPension: { label: 'Monthly Pension (₹)', desc: 'Pensioners receiving ₹10,000+ per month are excluded from PM-KISAN' },
    ownsAgriculturalLand: { label: 'Agricultural Land Ownership', desc: 'Must support land ownership Yes/No for agricultural schemes' },
    landholdingHectares: { label: 'Agricultural Landholding Size', desc: 'Land size in hectares for PM-KISAN and solar pump subsidies' },
    ownsPuccaHouse: { label: 'Pucca House Ownership', desc: 'Statutory criteria for Pradhan Mantri Awas Yojana (PMAY-G)' },
    hasBPLCard: { label: 'BPL / Ration Card', desc: 'Entitlement for subsidized welfare, food, and housing schemes' },
    isBankDefaulter: { label: 'Bank Loan Default Status', desc: 'Statutory criteria for Kisan Credit Card (KCC) and institutional credit' },
    socialCategory: { label: 'Social Category', desc: 'General, OBC, SC, ST, EWS for special quota considerations' },
    isDifferentlyAbled: { label: 'Differently Abled (PwD)', desc: 'Enables priority benefits and higher financial assistance' },
  },
  hi: {
    age: { label: 'आयु', desc: 'आयु-आधारित योजनाओं और वृद्धावस्था पेंशन के लिए आवश्यक' },
    gender: { label: 'लिंग', desc: 'महिला कल्याण और मातृत्व अनुदान योजनाओं के लिए आवश्यक' },
    state: { label: 'राज्य / केंद्र शासित प्रदेश', desc: 'राज्य-स्तरीय पात्रता और क्षेत्रीय लाभ निर्धारित करता है' },
    occupation: { label: 'मुख्य व्यवसाय', desc: 'किसान, रेहड़ी-पटरी वेंडर और श्रमिक योजनाओं की पहचान करता है' },
    farmerType: { label: 'किसान / काश्तकार श्रेणी', desc: 'भूमि मालिक, बटाईदार/पट्टेदार किसान या पशुपालन/संबद्ध क्षेत्र' },
    annualIncome: { label: 'वार्षिक पारिवारिक आय', desc: 'सब्सिडी और आवास अनुदान की आय सीमा के लिए आवश्यक' },
    paysIncomeTax: { label: 'आयकर दाता', desc: 'पीएम-किसान, पीएम-केएमवाई और प्रत्यक्ष योजनाओं से बहिष्करण शर्त' },
    hasRegularGovtJob: { label: 'सरकारी / पीएसयू नौकरी', desc: 'सरकारी कर्मचारी और उनके परिवार प्रत्यक्ष नकद योजनाओं से बाहर हैं' },
    monthlyPension: { label: 'मासिक पेंशन (₹)', desc: '₹10,000+ प्रति माह पेंशन पाने वाले पीएम-किसान से बाहर हैं' },
    ownsAgriculturalLand: { label: 'कृषि भूमि का स्वामित्व', desc: 'कृषि योजनाओं के लिए भूमि स्वामित्व हाँ/नहीं आवश्यक है' },
    landholdingHectares: { label: 'कृषि भूमि का आकार (हेक्टेयर)', desc: 'पीएम-किसान और सोलर पंप सब्सिडी हेतु हेक्टेयर में भूमि आकार' },
    ownsPuccaHouse: { label: 'पक्के मकान का स्वामित्व', desc: 'प्रधानमंत्री आवास योजना (पीएमएवाई) के लिए वैधानिक मानदंड' },
    hasBPLCard: { label: 'बीपीएल / राशन कार्ड', desc: 'सब्सिडी वाले भोजन, राशन और आवास योजनाओं के लिए पात्रता' },
    isBankDefaulter: { label: 'बैंक ऋण डिफ़ॉल्ट स्थिति', desc: 'किसान क्रेडिट कार्ड (KCC) और संस्थागत ऋण के लिए वैधानिक शर्त' },
    socialCategory: { label: 'सामाजिक श्रेणी', desc: 'विशेष आरक्षण और योजनाओं के लिए सामान्य, ओबीसी, एससी, एसटी, ईडब्ल्यूएस' },
    isDifferentlyAbled: { label: 'दिव्यांगता (दिव्यांगजन)', desc: 'प्राथमिकता लाभ और उच्चतर वित्तीय सहायता प्रदान करता है' },
  },
  kn: {
    age: { label: 'ವಯಸ್ಸು', desc: 'ವಯೋಮಾನ ಆಧಾರಿತ ಯೋಜನೆಗಳು ಮತ್ತು ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿಗಾಗಿ ಅಗತ್ಯ' },
    gender: { label: 'ಲಿಂಗ', desc: 'ಮಹಿಳಾ ಕಲ್ಯಾಣ ಮತ್ತು ಮಾತೃತ್ವ ಧನಸಹಾಯ ಯೋಜನೆಗಳಿಗೆ ಅಗತ್ಯ' },
    state: { label: 'ರಾಜ್ಯ / ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ', desc: 'ರಾಜ್ಯ ಮಟ್ಟದ ಅರ್ಹತೆ ಮತ್ತು ಪ್ರಾದೇಶಿಕ ಕೋಟಾವನ್ನು ನಿರ್ಧರಿಸುತ್ತದೆ' },
    occupation: { label: 'ಮುಖ್ಯ ಕಸುಬು / ಉದ್ಯೋಗ', desc: 'ರೈತ, ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿ ಮತ್ತು ಕಾರ್ಮಿಕರ ಸೌಲಭ್ಯಗಳನ್ನು ಗುರುತಿಸುತ್ತದೆ' },
    farmerType: { label: 'ರೈತ / ಕೃಷಿಕ ವರ್ಗ', desc: 'ಭೂಮಾಲೀಕ, ಗೇಣಿದಾರ ಅಥವಾ ಕೃಷಿ ಪೂರಕ ಕ್ಷೇತ್ರದ ಕಾರ್ಮಿಕ' },
    annualIncome: { label: 'ವಾರ್ಷಿಕ ಕುಟುಂಬ ಆದಾಯ', desc: 'ಸಬ್ಸಿಡಿ ಮತ್ತು ವಸತಿ ಅನುದಾನಗಳ ಆದಾಯ ಮಿತಿಗಾಗಿ ಅಗತ್ಯ' },
    paysIncomeTax: { label: 'ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿದಾರರು', desc: 'ಪಿಎಂ-ಕಿಸಾನ್ ಮತ್ತು ನೇರ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳಿಂದ ಹೊರಗಿಡುವ ಮಾನದಂಡ' },
    hasRegularGovtJob: { label: 'ಸರ್ಕಾರಿ / ಪಿಎಸ್‌ಯು ಉದ್ಯೋಗ', desc: 'ಸರ್ಕಾರಿ ನೌಕರರು ಮತ್ತು ಅವರ ಕುಟುಂಬವನ್ನು ನಗದು ವರ್ಗಾವಣೆಯಿಂದ ಹೊರಗಿಡಲಾಗುತ್ತದೆ' },
    monthlyPension: { label: 'ಮಾಸಿಕ ಪಿಂಚಣಿ (₹)', desc: 'ತಿಂಗಳಿಗೆ ₹10,000+ ಪಿಂಚಣಿ ಪಡೆಯುವವರು ಪಿಎಂ-ಕಿಸಾನ್‌ನಿಂದ ಹೊರಗುಳಿಯುತ್ತಾರೆ' },
    ownsAgriculturalLand: { label: 'ಕೃಷಿ ಭೂಮಿ ಮಾಲೀಕತ್ವ', desc: 'ಕೃಷಿ ಯೋಜನೆಗಳಿಗಾಗಿ ಕೃಷಿ ಭೂಮಿ ಮಾಲೀಕತ್ವ ಹೌದು/ಇಲ್ಲ ಅಗತ್ಯ' },
    landholdingHectares: { label: 'ಕೃಷಿ ಭೂಮಿಯ ವಿಸ್ತೀರ್ಣ (ಹೆಕ್ಟೇರ್)', desc: 'ಪಿಎಂ-ಕಿಸಾನ್ ಮತ್ತು ಸೋಲಾರ್ ಪಂಪ್ ಸಬ್ಸಿಡಿಗಾಗಿ ಹೆಕ್ಟೇರ್‌ಗಳಲ್ಲಿ ಭೂಮಿ ವಿಸ್ತೀರ್ಣ' },
    ownsPuccaHouse: { label: 'ಪಕ್ಕಾ ಮನೆ ಮಾಲೀಕತ್ವ', desc: 'ಪ್ರಧಾನ ಮಂತ್ರಿ ಆವಾಸ್ ಯೋಜನೆ (PMAY-G) ಗೆ ಶಾಸನಬದ್ಧ ಮಾನದಂಡ' },
    hasBPLCard: { label: 'ಬಿಪಿಎಲ್ / ರೇಷನ್ ಕಾರ್ಡ್', desc: 'ಸಬ್ಸಿಡಿ ಆಹಾರ, ಪಡಿತರ ಮತ್ತು ವಸತಿ ಯೋಜನೆಗಳಿಗೆ ಅಗತ್ಯ ದಾಖಲೆ' },
    isBankDefaulter: { label: 'ಬ್ಯಾಂಕ್ ಸಾಲ ಬಾಕಿ ಸ್ಥಿತಿ', desc: 'ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ (KCC) ಮತ್ತು ಸಾಂಸ್ಥಿಕ ಸಾಲಗಳ ಶಾಸನಬದ್ಧ ಷರತ್ತು' },
    socialCategory: { label: 'ಸಾಮಾಜಿಕ ವರ್ಗ', desc: 'ವಿಶೇಷ ಮೀಸಲಾತಿ ಯೋಜನೆಗಳಿಗಾಗಿ ಸಾಮಾನ್ಯ, ಒಬಿಸಿ, ಎಸ್‌ಸಿ, ಎಸ್‌ಟಿ, ಇಡಬ್ಲ್ಯೂಎಸ್' },
    isDifferentlyAbled: { label: 'ವಿಶೇಷ ಚೇತನರು (PwD)', desc: 'ಆದ್ಯತೆ ಪ್ರಯೋಜನಗಳು ಮತ್ತು ಹೆಚ್ಚಿನ ಆರ್ಥಿಕ ನೆರವು ಒದಗಿಸುತ್ತದೆ' },
  },
  te: {
    age: { label: 'వయస్సు', desc: 'వయోపరిమితి ఆధారిత పథకాలు మరియు వృద్ధాప్య పెన్షన్ల కోసం అవసరం' },
    gender: { label: 'లింగం', desc: 'మహిళా సంక్షేమం మరియు ప్రసూతి గ్రాంట్ల కోసం అవసరం' },
    state: { label: 'రాష్ట్రం / కేంద్రపాలిత ప్రాంతం', desc: 'రాష్ట్ర స్థాయి అర్హత మరియు ప్రాంతీయ కోటాను నిర్ణయిస్తుంది' },
    occupation: { label: 'ప్రధాన వృత్తి / జీవనోపాధి', desc: 'రైతు, వీధి వ్యాపారి మరియు కార్మిక ప్రయోజనాలను గుర్తిస్తుంది' },
    farmerType: { label: 'రైతు / సాగుదారు వర్గం', desc: 'భూ యజమాని, కౌలు రైతు లేదా అనుబంధ రంగాల కార్మికుడు' },
    annualIncome: { label: 'వార్షిక కుటుంబ ఆదాయం', desc: 'సబ్సిడీలు మరియు గృహ గ్రాంట్ల ఆదాయ పరిమితికి అవసరం' },
    paysIncomeTax: { label: 'ఆదాయపు పన్ను చెల్లింపుదారు', desc: 'పీఎం-కిసాన్ మరియు ప్రత్యక్ష సంక్షేమ పథకాల మినహాయింపు నిబంధన' },
    hasRegularGovtJob: { label: 'ప్రభుత్వ / పిఎస్‌యు ఉద్యోగం', desc: 'ప్రభుత్వ ఉద్యోగులు మరియు వారి కుటుంబాలు నగదు బదిలీల నుండి మినహాయించబడ్డాయి' },
    monthlyPension: { label: 'నెలవారీ పెన్షన్ (₹)', desc: 'నెలకు ₹10,000+ పెన్షన్ పొందే వారు పీఎం-కిసాన్ నుండి మినహాయించబడ్డారు' },
    ownsAgriculturalLand: { label: 'వ్యవసాయ భూమి యాజమాన్యం', desc: 'వ్యవసాయ పథకాల కోసం భూమి యాజమాన్యం అవును/కాదు అవసరం' },
    landholdingHectares: { label: 'వ్యవసాయ భూమి పరిమాణం (హెక్టార్లు)', desc: 'పీఎం-కిసాన్ మరియు సౌర పంపు సబ్సిడీల కోసం హెక్టార్లలో భూమి పరిమాణం' },
    ownsPuccaHouse: { label: 'పక్కా ఇల్లు యాజమాన్యం', desc: 'ప్రధాన మంత్రి ఆవాస్ యోజన (PMAY-G) కొరకు చట్టబద్ధమైన నిబంధన' },
    hasBPLCard: { label: 'బిపిఎల్ / రేషన్ కార్డు', desc: 'సబ్సిడీ ఆహార ధాన్యాలు మరియు గృహ పథకాల కొరకు అవసరం' },
    isBankDefaulter: { label: 'బ్యాంకు రుణం డిఫాల్ట్ స్థితి', desc: 'కిసాన్ క్రెడిట్ కార్డ్ (KCC) మరియు సంస్థాగత రుణాల చట్టబద్ధమైన నిబంధన' },
    socialCategory: { label: 'సామాజిక వర్గం', desc: 'ప్రత్యేక కోటా పథకాల కొరకు జనరల్, ఓబీసీ, ఎస్సీ, ఎస్టీ, ఈడబ్ల్యూఎస్' },
    isDifferentlyAbled: { label: 'దివ్యాంగులు (PwD)', desc: 'ప్రాధాన్యతా ప్రయోజనాలు మరియు అధిక ఆర్థిక సహాయాన్ని అందిస్తుంది' },
  },
};

export const ProfileConfirmation: React.FC = () => {
  const navigate = useNavigate();
  const {
    userProfile,
    attributeSources,
    hasConfirmedProfile,
    setHasConfirmedProfile,
    updateUserProfile,
    clearProfileAttribute,
    resetSession,
    language,
  } = useApp();

  const currentLangInfo = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];

  // AI Voice & Text Profile Filler state
  const [aiInputText, setAiInputText] = useState('');
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [aiFeedback, setAiFeedback] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  // Single-attribute modal editing state
  const [activeEditField, setActiveEditField] = useState<keyof UserProfile | null>(null);
  const [editValue, setEditValue] = useState<any>('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const criteriaKeys: (keyof UserProfile)[] = [
    'age',
    'gender',
    'state',
    'occupation',
    'farmerType',
    'annualIncome',
    'paysIncomeTax',
    'hasRegularGovtJob',
    'monthlyPension',
    'ownsAgriculturalLand',
    'landholdingHectares',
    'ownsPuccaHouse',
    'hasBPLCard',
    'isBankDefaulter',
    'socialCategory',
    'isDifferentlyAbled',
  ];

  const filledCount = criteriaKeys.filter((key) => {
    const val = userProfile[key];
    return val !== undefined && val !== null && val !== '';
  }).length;
  const completenessPercent = Math.round((filledCount / criteriaKeys.length) * 100);

  // AI Profile Extraction handler
  const handleAiProfileFill = async (textToProcess: string) => {
    const clean = textToProcess.trim();
    if (!clean) return;
    setIsAiProcessing(true);
    setAiFeedback(null);
    try {
      const sid = getSessionId();
      const res = await sendChatMessage({
        message: clean,
        language,
        session_id: sid,
      });

      if (res && res.active_profile) {
        const ap = res.active_profile;
        const updates: Partial<UserProfile> = {};

        if (ap.age !== undefined) updates.age = Number(ap.age);
        if (ap.gender) updates.gender = ap.gender.charAt(0).toUpperCase() + ap.gender.slice(1).toLowerCase();
        if (ap.state) updates.state = ap.state;
        if (ap.occupation) updates.occupation = ap.occupation;
        if (ap.owns_agricultural_land !== undefined) updates.ownsAgriculturalLand = Boolean(ap.owns_agricultural_land);
        if (ap.landholding_hectares !== undefined) updates.landholdingHectares = Number(ap.landholding_hectares);
        if (ap.annual_income_inr !== undefined) updates.annualIncome = Number(ap.annual_income_inr);
        if (ap.pays_income_tax !== undefined) updates.paysIncomeTax = Boolean(ap.pays_income_tax);
        if (ap.has_regular_govt_job !== undefined) updates.hasRegularGovtJob = Boolean(ap.has_regular_govt_job);
        if (ap.monthly_pension_inr !== undefined) updates.monthlyPension = Number(ap.monthly_pension_inr);
        if (ap.has_bpl_card !== undefined) updates.hasBPLCard = Boolean(ap.has_bpl_card);
        if (ap.is_bank_defaulter !== undefined) updates.isBankDefaulter = Boolean(ap.is_bank_defaulter);
        if (ap.social_category) updates.socialCategory = ap.social_category;
        if (ap.owns_pucca_house !== undefined) updates.ownsPuccaHouse = Boolean(ap.owns_pucca_house);
        if (ap.is_differently_abled !== undefined) updates.isDifferentlyAbled = Boolean(ap.is_differently_abled);

        const count = Object.keys(updates).length;
        if (count > 0) {
          updateUserProfile(updates, 'detected');
          setAiFeedback(`✨ AI successfully extracted ${count} profile attributes!`);
          setAiInputText('');
        } else {
          setAiFeedback('No specific attributes detected. Please include your age, occupation, state, or land details.');
        }
      }
    } catch (err: any) {
      setAiFeedback(err?.message || 'Could not process details. Please try again or use the buttons below.');
    } finally {
      setIsAiProcessing(false);
    }
  };

  const handleVoiceInput = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please type your details.');
      return;
    }
    try {
      const recognition = new SpeechRecognition();
      const localeMap: Record<string, string> = {
        en: 'en-IN',
        hi: 'hi-IN',
        kn: 'kn-IN',
        te: 'te-IN',
      };
      recognition.lang = localeMap[language] || 'en-IN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      setIsRecording(true);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setAiInputText(transcript);
          handleAiProfileFill(transcript);
        }
        setIsRecording(false);
      };
      recognition.onerror = () => {
        setIsRecording(false);
      };
      recognition.onend = () => {
        setIsRecording(false);
      };
      recognition.start();
    } catch {
      setIsRecording(false);
    }
  };

  const openSingleFieldEdit = (field: keyof UserProfile) => {
    setActiveEditField(field);
    setValidationError(null);
    setSaveSuccessMsg(null);
    const curr = userProfile[field];
    if (curr !== undefined && curr !== null) {
      setEditValue(curr);
    } else {
      setEditValue('');
    }
  };

  const handleSaveSingleField = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeEditField) return;
    setValidationError(null);

    let finalVal: any = editValue;

    // Field-specific validation
    if (activeEditField === 'age') {
      if (String(editValue).trim() !== '') {
        const n = Number(editValue);
        if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0 || n > 120) {
          setValidationError('Please enter a valid age between 0 and 120.');
          return;
        }
        finalVal = n;
      } else {
        finalVal = undefined;
      }
    } else if (activeEditField === 'annualIncome') {
      if (String(editValue).trim() !== '') {
        const n = Number(editValue);
        if (!Number.isFinite(n) || n < 0) {
          setValidationError('Please enter a positive income amount.');
          return;
        }
        finalVal = n;
      } else {
        finalVal = undefined;
      }
    } else if (activeEditField === 'monthlyPension') {
      if (String(editValue).trim() !== '') {
        const n = Number(editValue);
        if (!Number.isFinite(n) || n < 0) {
          setValidationError('Please enter a positive pension amount in ₹.');
          return;
        }
        finalVal = n;
      } else {
        finalVal = undefined;
      }
    } else if (activeEditField === 'landholdingHectares') {
      if (String(editValue).trim() !== '') {
        const n = Number(editValue);
        if (!Number.isFinite(n) || n < 0) {
          setValidationError('Please enter valid landholding size in hectares.');
          return;
        }
        finalVal = n;
      } else {
        finalVal = undefined;
      }
    } else if (
      activeEditField === 'isBankDefaulter' ||
      activeEditField === 'hasBPLCard' ||
      activeEditField === 'paysIncomeTax' ||
      activeEditField === 'hasRegularGovtJob' ||
      activeEditField === 'ownsPuccaHouse' ||
      activeEditField === 'isDifferentlyAbled' ||
      activeEditField === 'ownsAgriculturalLand'
    ) {
      if (editValue === 'true' || editValue === true) finalVal = true;
      else if (editValue === 'false' || editValue === false) finalVal = false;
      else finalVal = undefined;
    }

    if (finalVal === undefined || finalVal === '') {
      clearProfileAttribute(activeEditField);
    } else {
      const updates: Partial<UserProfile> = { [activeEditField]: finalVal };
      if (activeEditField === 'farmerType') {
        const ftStr = String(finalVal);
        if (ftStr.includes('Landowner')) updates.ownsAgriculturalLand = true;
        if (ftStr.includes('Tenant') || ftStr.includes('Sharecropper')) updates.isTenantFarmer = true;
        if (ftStr.includes('Animal') || ftStr.includes('Allied')) updates.isAlliedActivityWorker = true;
      }
      if (activeEditField === 'landholdingHectares' && Number(finalVal) > 0) {
        updates.ownsAgriculturalLand = true;
      }
      updateUserProfile(updates, 'user');
    }

    setSaveSuccessMsg('Attribute updated successfully!');
    setTimeout(() => {
      setActiveEditField(null);
      setSaveSuccessMsg(null);
    }, 500);
  };

  const getAttributeDisplay = (key: keyof UserProfile): { valueText: string; isSet: boolean } => {
    const val = userProfile[key];
    if (val === undefined || val === null || val === '') {
      const unsetMap: Record<Language, string> = {
        en: 'Not provided / Unset',
        hi: 'प्रदान नहीं किया गया / असेट',
        kn: 'ನೀಡಲಾಗಿಲ್ಲ / ನಿಗದಿಪಡಿಸಿಲ್ಲ',
        te: 'అందించలేదు / సెట్ చేయలేదు',
      };
      return { valueText: unsetMap[language] || unsetMap.en, isSet: false };
    }
    if (key === 'age') {
      const unitMap: Record<Language, string> = {
        en: 'years',
        hi: 'वर्ष',
        kn: 'ವರ್ಷಗಳು',
        te: 'సంవత్సరాలు',
      };
      return { valueText: `${val} ${unitMap[language] || unitMap.en}`, isSet: true };
    }
    if (key === 'annualIncome') {
      const perYearMap: Record<Language, string> = {
        en: '/ year',
        hi: '/ वर्ष',
        kn: '/ ವರ್ಷ',
        te: '/ సంవత్సరం',
      };
      return { valueText: `₹${Number(val).toLocaleString('en-IN')} ${perYearMap[language] || perYearMap.en}`, isSet: true };
    }
    if (key === 'monthlyPension') {
      const perMonthMap: Record<Language, string> = {
        en: '/ month',
        hi: '/ माह',
        kn: '/ ತಿಂಗಳು',
        te: '/ నెల',
      };
      return { valueText: `₹${Number(val).toLocaleString('en-IN')} ${perMonthMap[language] || perMonthMap.en}`, isSet: true };
    }
    if (key === 'landholdingHectares') {
      const haMap: Record<Language, string> = {
        en: 'hectares',
        hi: 'हेक्टेयर',
        kn: 'ಹೆಕ್ಟೇರ್',
        te: 'హెక్టార్లు',
      };
      return { valueText: `${val} ${haMap[language] || haMap.en}`, isSet: true };
    }
    if (key === 'isBankDefaulter') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, has loan default', 'No default (clean credit)'],
        hi: ['हाँ, बैंक ऋण बकाया है', 'कोई डिफ़ॉल्ट नहीं (साफ क्रेडिट)'],
        kn: ['ಹೌದು, ಸಾಲ ಬಾಕಿ ಇದೆ', 'ಯಾವುದೇ ಬಾಕಿ ಇಲ್ಲ (ಉತ್ತಮ ಕ್ರೆಡಿಟ್)'],
        te: ['అవును, బ్యాంకు రుణం బకాయి ఉంది', 'డిఫాల్ట్ లేదు (క్లీన్ క్రెడిట్)'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'hasBPLCard') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, has BPL/Ration card', 'No BPL card'],
        hi: ['हाँ, बीपीएल/राशन कार्ड उपलब्ध है', 'बीपीएल कार्ड नहीं है'],
        kn: ['ಹೌದು, ಬಿಪಿಎಲ್/ರೇಷನ್ ಕಾರ್ಡ್ ಇದೆ', 'ಬಿಪಿಎಲ್ ಕಾರ್ಡ್ ಇಲ್ಲ'],
        te: ['అవును, బిపిఎల్/రేషన్ కార్డు ఉంది', 'బిపిఎల్ కార్డు లేదు'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'paysIncomeTax') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, Income Tax Payer', 'Non-taxpayer (exempt)'],
        hi: ['हाँ, आयकर दाता', 'गैर-करदाता (छूट प्राप्त)'],
        kn: ['ಹೌದು, ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿದಾರರು', 'ತೆರಿಗೆ ಮುಕ್ತ (ತೆರಿಗೆದಾರರಲ್ಲ)'],
        te: ['అవును, ఆదాయపు పన్ను చెల్లింపుదారు', 'పన్ను చెల్లించని వారు (మినహాయింపు)'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'hasRegularGovtJob') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, regular Govt/PSU job', 'No government job'],
        hi: ['हाँ, सरकारी/पीएसयू नौकरी है', 'सरकारी नौकरी नहीं है'],
        kn: ['ಹೌದು, ಸರ್ಕಾರಿ/ಪಿಎಸ್‌ಯು ಉದ್ಯೋಗವಿದೆ', 'ಸರ್ಕಾರಿ ಉದ್ಯೋಗವಿಲ್ಲ'],
        te: ['అవును, రెగ్యులర్ ప్రభుత్వ/పిఎస్‌యు ఉద్యోగం ఉంది', 'ప్రభుత్వ ఉద్యోగం లేదు'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'ownsPuccaHouse') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, owns pucca house', 'No pucca house (kutcha/homeless)'],
        hi: ['हाँ, पक्का मकान है', 'पक्का मकान नहीं है (कच्चा/बेघर)'],
        kn: ['ಹೌದು, ಪಕ್ಕಾ ಮನೆ ಇದೆ', 'ಪಕ್ಕಾ ಮನೆ ಇಲ್ಲ (ಕಚ್ಚಾ/ಮನೆರಹಿತ)'],
        te: ['అవును, పక్కా ఇల్లు ఉంది', 'పక్కా ఇల్లు లేదు (కచ్చా/నిరాశ్రయులు)'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'isDifferentlyAbled') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, differently abled (PwD)', 'No disability'],
        hi: ['हाँ, दिव्यांग (दिव्यांगजन)', 'कोई दिव्यांगता नहीं'],
        kn: ['ಹೌದು, ವಿಶೇಷ ಚೇತನರು (PwD)', 'ಯಾವುದೇ ಅಂಗವೈಕಲ್ಯವಿಲ್ಲ'],
        te: ['అవును, దివ్యాంగులు (PwD)', 'వైకల్యం లేదు'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'ownsAgriculturalLand') {
      const texts: Record<Language, [string, string]> = {
        en: ['Yes, owns land', 'No agricultural land'],
        hi: ['हाँ, कृषि भूमि है', 'कृषि भूमि नहीं है'],
        kn: ['ಹೌದು, ಕೃಷಿ ಭೂಮಿ ಇದೆ', 'ಕೃಷಿ ಭೂಮಿ ಇಲ್ಲ'],
        te: ['అవును, వ్యవసాయ భూమి ఉంది', 'వ్యవసాయ భూమి లేదు'],
      };
      const [yes, no] = texts[language] || texts.en;
      return { valueText: val ? yes : no, isSet: true };
    }
    if (key === 'occupation') {
      const found = LOCALIZED_OCCUPATION_MAP[language]?.find((o) => o.key === val);
      if (found) return { valueText: found.label, isSet: true };
    }
    if (key === 'farmerType') {
      const found = LOCALIZED_FARMER_TYPES_MAP[language]?.find((f) => f.key === val);
      if (found) return { valueText: found.label, isSet: true };
    }
    if (key === 'gender') {
      const found = LOCALIZED_GENDERS_MAP[language]?.find((g) => g.key.toLowerCase() === String(val).toLowerCase());
      if (found) return { valueText: found.label, isSet: true };
    }
    if (key === 'socialCategory') {
      const found = LOCALIZED_CASTES_MAP[language]?.find((c) => c.key === val);
      if (found) return { valueText: found.label, isSet: true };
    }
    return { valueText: String(val), isSet: true };
  };

  const renderSourceBadge = (key: keyof UserProfile, isSet: boolean) => {
    if (!isSet) {
      const unsetLabel = {
        en: 'Unset',
        hi: 'असेट',
        kn: 'ನಿಗದಿಪಡಿಸಿಲ್ಲ',
        te: 'సెట్ చేయలేదు',
      }[language] || 'Unset';
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-ink/50 bg-sand/30 px-2 py-0.5 rounded-full border border-sand">
          <HelpCircle className="w-3 h-3" />
          <span>{unsetLabel}</span>
        </span>
      );
    }
    const source = attributeSources[key] || 'user';
    if (source === 'detected') {
      const aiLabel = {
        en: 'From chat / AI',
        hi: 'चैट / AI से',
        kn: 'ಚಾಟ್ / AI ನಿಂದ',
        te: 'చాట్ / AI నుండి',
      }[language] || 'From chat / AI';
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-300">
          <Sparkles className="w-3 h-3 text-amber-600" />
          <span>{aiLabel}</span>
        </span>
      );
    }
    const confirmedLabel = {
      en: 'Confirmed',
      hi: 'पुष्टि की गई',
      kn: 'ದೃಢಪಡಿಸಲಾಗಿದೆ',
      te: 'ధೃವೀకరించಬడింది',
    }[language] || 'Confirmed';
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-300">
        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
        <span>{confirmedLabel}</span>
      </span>
    );
  };

  const activeLangCards = LOCALIZED_ATTRIBUTE_CARDS[language] || LOCALIZED_ATTRIBUTE_CARDS.en;
  const attributeCards: {
    key: keyof UserProfile;
    label: string;
    desc: string;
  }[] = criteriaKeys.map((key) => ({
    key,
    label: activeLangCards[key]?.label || String(key),
    desc: activeLangCards[key]?.desc || '',
  }));

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header
        title={t('navProfile', language)}
        subtitle={
          language === 'hi'
            ? 'नागरिक प्रोफ़ाइल एवं AI सहायक'
            : language === 'kn'
            ? 'ನಾಗರಿಕ ಪ್ರೊಫೈಲ್ ಮತ್ತು AI ಸಹಾಯಕ'
            : language === 'te'
            ? 'పౌర ప్రొఫైల్ & AI సహాయకుడు'
            : 'Citizen Profile & AI Assistant'
        }
        showBack
      />

      <main className="max-w-3xl mx-auto px-4 py-5 space-y-5">
        {/* Profile Header & Completeness */}
        <div className="bg-surface rounded-2xl p-5 border border-sand shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-full bg-forest text-white flex items-center justify-center font-bold text-lg shadow-sm flex-shrink-0">
                <User className="w-6 h-6" />
              </div>
              <div>
                <h1 className="font-heading font-bold text-lg text-ink">
                  {language === 'hi'
                    ? 'नागरिक पात्रता प्रोफ़ाइल'
                    : language === 'kn'
                    ? 'ನಾಗರಿಕ ಅರ್ಹತಾ ಪ್ರೊಫೈಲ್'
                    : language === 'te'
                    ? 'పౌర అర్హత ప్రొఫైల్'
                    : 'Citizen Eligibility Profile'}
                </h1>
                <p className="text-xs text-ink/65">
                  {language === 'hi'
                    ? 'हमेशा संपादन योग्य • शून्य स्थायी व्यक्तिगत डेटा • नियमों द्वारा सटीक मूल्यांकन'
                    : language === 'kn'
                    ? 'ಯಾವಾಗಲೂ ಸಂಪಾದಿಸಬಹುದಾಗಿದೆ • ಯಾವುದೇ ಶಾಶ್ವತ ಡೇಟಾ ಇಲ್ಲ • ಕಟ್ಟುನಿಟ್ಟಾದ ನಿಯಮಗಳೊಂದಿಗೆ ಮೌಲ್ಯಮಾಪನ'
                    : language === 'te'
                    ? 'ఎల్లప్పుడూ సవరించవచ్చు • శాశ్వత వ్యక్తిగత డేటా లేదు • కచ్చితమైన నిబంధనలతో మూల్యాంకనం'
                    : 'Always editable • Zero permanent PII • Evaluated strictly with deterministic rules'}
                </p>
              </div>
            </div>

            {filledCount > 0 && (
              <button
                type="button"
                onClick={resetSession}
                className="text-xs font-semibold text-rose-700 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded-full border border-rose-200 transition-colors flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>
                  {language === 'hi'
                    ? 'मेरी जानकारी साफ़ करें'
                    : language === 'kn'
                    ? 'ನನ್ನ ಮಾಹಿತಿ ಅಳಿಸಿ'
                    : language === 'te'
                    ? 'నా సమాచారాన్ని క్లియర్ చేయండి'
                    : 'Clear my information'}
                </span>
              </button>
            )}
          </div>

          {/* Completeness Bar */}
          <div className="pt-2 border-t border-sand space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-ink">
                {language === 'hi'
                  ? 'प्रोफ़ाइल पूर्णता'
                  : language === 'kn'
                  ? 'ಪ್ರೊಫೈಲ್ ಪೂರ್ಣತೆ'
                  : language === 'te'
                  ? 'ప్రొಫైల్ సంపూర్ణత'
                  : 'Profile Completeness'}
              </span>
              <span className="font-bold text-forest">
                {filledCount}{' '}
                {language === 'hi'
                  ? 'में से'
                  : language === 'kn'
                  ? 'ರ ಪೈಕಿ'
                  : language === 'te'
                  ? 'లో'
                  : 'of'}{' '}
                {criteriaKeys.length}{' '}
                {language === 'hi'
                  ? 'विशेषताएं सेट'
                  : language === 'kn'
                  ? 'ವಿವರಗಳು ನಮೂದಿಸಲಾಗಿದೆ'
                  : language === 'te'
                  ? 'లక్షణాలు నమోదు చేయబడ్డాయి'
                  : 'attributes set'}{' '}
                ({completenessPercent}%)
              </span>
            </div>
            <div className="w-full bg-sand/40 h-2.5 rounded-full overflow-hidden">
              <div
                className="bg-forest h-full rounded-full transition-all duration-300"
                style={{ width: `${completenessPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* AI LLM Smart Profile Voice/Text Setup Widget */}
        <div className="bg-gradient-to-br from-forest/5 via-sage/15 to-surface rounded-2xl p-4 sm:p-5 border border-forest/30 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-forest animate-pulse" />
              <h2 className="font-heading font-bold text-sm text-ink">
                {language === 'hi'
                  ? 'AI स्मार्ट प्रोफ़ाइल सेटअप (वॉइस और टेक्स्ट)'
                  : language === 'kn'
                  ? 'AI ಸ್ಮಾರ್ಟ್ ಪ್ರೊಫೈಲ್ ಸೆಟಪ್ (ಧ್ವನಿ ಮತ್ತು ಪಠ್ಯ)'
                  : language === 'te'
                  ? 'AI స్మార్ట్ ప్రొఫైల్ సెటప్ (వాయిస్ & టెక్స్ట్)'
                  : 'AI Smart Profile Setup (Voice & Text)'}
              </h2>
            </div>
            <span className="text-[11px] font-bold text-forest bg-forest/10 px-2 py-0.5 rounded-md">
              {language === 'hi'
                ? 'भारतीय भाषा NLU'
                : language === 'kn'
                ? 'ಭಾರತೀಯ ಭಾಷಾ NLU'
                : language === 'te'
                ? 'భారతీయ భాష NLU'
                : 'Indic NLU'}
            </span>
          </div>
          <p className="text-xs text-ink/75 leading-relaxed">
            {language === 'hi'
              ? 'अपनी स्थिति स्वाभाविक रूप से बोलें या लिखें (उदा. "मैं कर्नाटक से 45 वर्षीय महिला किसान हूँ, 2 एकड़ जमीन है और कोई आयकर नहीं भरती")। हमारा AI सीधे सभी पात्रता विवरण निकालता है।'
              : language === 'kn'
              ? 'ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ (ಉದಾ: "ನಾನು ಕರ್ನಾಟಕದ 45 ವರ್ಷದ ಮಹಿಳಾ ರೈತ, 2 ಎಕರೆ ಭೂಮಿ ಇದೆ ಮತ್ತು ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸುವುದಿಲ್ಲ"). ನಮ್ಮ AI ನೇರವಾಗಿ ವಿವರಗಳನ್ನು ನಮೂದಿಸುತ್ತದೆ.'
              : language === 'te'
              ? 'మీ వివరాలను సహజంగా మాట్లాడండి లేదా టైప్ చేయండి (ఉదా: "నేను కర్ణాటకకు చెందిన 45 ఏళ్ల మహిళా రైతును, 2 ఎకరాల భూమి ఉంది మరియు ఆదాయపు పన్ను చెల్లించను"). మా AI నేరుగా వివరాలను సంగ్రహిస్తుంది.'
              : 'Speak or type your situation naturally (e.g. "I am a 45-year-old female farmer from Karnataka with 2 acres land and no income tax"). Our AI extracts and maps all eligibility fields directly.'}
          </p>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={aiInputText}
                onChange={(e) => setAiInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAiProfileFill(aiInputText)}
                placeholder={
                  language === 'hi'
                    ? 'विवरण लिखें या बोलने के लिए माइक दबाएं...'
                    : language === 'kn'
                    ? 'ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಮಾತನಾಡಲು ಮೈಕ್ ಒತ್ತಿ...'
                    : language === 'te'
                    ? 'టైప్ చేయండి లేదా మాట్లాడటానికి మైక్ నొక్కండి...'
                    : 'Type or tap the mic to speak...'
                }
                className="w-full bg-surface border border-sand rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-ink focus:outline-none focus:ring-2 focus:ring-forest shadow-xs pr-10"
              />
              <button
                type="button"
                onClick={handleVoiceInput}
                className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors ${
                  isRecording ? 'bg-red-600 text-white animate-pulse' : 'text-forest hover:bg-forest/10'
                }`}
                title="Speak details"
              >
                <Mic className="w-4 h-4" />
              </button>
            </div>
            <button
              type="button"
              disabled={isAiProcessing || !aiInputText.trim()}
              onClick={() => handleAiProfileFill(aiInputText)}
              className="bg-forest hover:bg-forest-deep text-white font-bold px-4 py-2.5 rounded-xl text-xs sm:text-sm shadow-xs disabled:opacity-50 flex items-center justify-center gap-1.5 transition-transform active:scale-95"
            >
              {isAiProcessing
                ? language === 'hi'
                  ? 'पहचान जारी...'
                  : language === 'kn'
                  ? 'ಗುರುತಿಸಲಾಗುತ್ತಿದೆ...'
                  : language === 'te'
                  ? 'విశ్లేషిస్తోంది...'
                  : 'Extracting...'
                : language === 'hi'
                ? 'प्रोफ़ाइल ऑटो-भरें'
                : language === 'kn'
                ? 'ಪ್ರೊಫೈಲ್ ಸ್ವಯಂ ಭರ್ತಿ ಮಾಡಿ'
                : language === 'te'
                ? 'ప్రొಫైల్ ఆటో-ఫిల్ చేయండి'
                : 'Auto-Fill Profile'}
            </button>
          </div>

          {aiFeedback && (
            <div className="text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl p-2.5 flex items-center gap-2 animate-fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>{aiFeedback}</span>
            </div>
          )}
        </div>

        {/* 16 Comprehensive Always-Editable Attribute Cards */}
        <div className="space-y-3">
          <h2 className="font-heading font-bold text-sm text-ink px-1">
            {language === 'hi'
              ? `नागरिक विशेषताएं (${criteriaKeys.length})`
              : language === 'kn'
              ? `ನಾಗರಿಕ ವಿವರಗಳು (${criteriaKeys.length})`
              : language === 'te'
              ? `పౌర లక్షణాలు (${criteriaKeys.length})`
              : `Citizen Attributes (${criteriaKeys.length})`}
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {attributeCards.map((card) => {
              const { valueText, isSet } = getAttributeDisplay(card.key);
              return (
                <div
                  key={card.key}
                  className="bg-surface rounded-2xl p-4 border border-sand hover:border-forest/40 shadow-xs transition-all flex flex-col justify-between"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-heading font-bold text-xs text-ink uppercase tracking-wider">
                        {card.label}
                      </span>
                      {renderSourceBadge(card.key, isSet)}
                    </div>
                    <p className="text-[11px] text-ink/60 leading-tight">
                      {card.desc}
                    </p>
                    <div className={`text-sm pt-1 ${isSet ? 'font-bold text-forest' : 'font-normal italic text-ink/40'}`}>
                      {valueText}
                    </div>
                  </div>

                  <div className="pt-3 mt-3 border-t border-sand/60 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => openSingleFieldEdit(card.key)}
                      className="text-xs font-bold text-forest hover:text-forest-deep bg-sage/50 hover:bg-sage px-3 py-1.5 rounded-xl border border-forest/20 flex items-center gap-1.5 transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>
                        {isSet
                          ? language === 'hi'
                            ? 'संपादित करें'
                            : language === 'kn'
                            ? 'ಸಂಪಾದಿಸಿ'
                            : language === 'te'
                            ? 'సవరించు'
                            : 'Edit'
                          : language === 'hi'
                          ? 'मान दर्ज करें'
                          : language === 'kn'
                          ? 'ನಮೂದಿಸಿ'
                          : language === 'te'
                          ? 'నమోదు చేయి'
                          : 'Set Value'}
                      </span>
                    </button>
                    {isSet && (
                      <button
                        type="button"
                        onClick={() => clearProfileAttribute(card.key)}
                        aria-label={`Clear ${card.label}`}
                        className="p-1.5 text-ink/40 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-colors"
                        title="Clear attribute"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Zero PII Privacy Notice */}
        <div className="bg-forest/5 border border-forest/20 rounded-2xl p-4 flex items-start gap-3 text-xs text-forest-deep">
          <ShieldCheck className="w-5 h-5 text-forest flex-shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <span className="font-bold">
              {language === 'hi'
                ? 'शून्य स्थायी व्यक्तिगत डेटा संग्रहण: '
                : language === 'kn'
                ? 'ಶೂನ್ಯ ಶಾಶ್ವತ PII ಸಂಗ್ರಹಣೆ: '
                : language === 'te'
                ? 'జీరో శాశ్వత PII నిల్వ: '
                : 'Zero Permanent PII Storage: '}
            </span>
            {language === 'hi'
              ? 'सभी विवरण केवल सक्रिय सत्र मेमोरी में कल्याणकारी पात्रता के मूल्यांकन हेतु रखे जाते हैं। इन्हें कभी डिस्क या स्थायी डेटाबेस में संग्रहीत नहीं किया जाता है।'
              : language === 'kn'
              ? 'ಅರ್ಹತೆಯನ್ನು ನಿರ್ಣಯಿಸಲು ಎಲ್ಲಾ ವಿವರಗಳನ್ನು ಸಕ್ರಿಯ ಸೆಷನ್ ಮೆಮೊರಿಯಲ್ಲಿ ಮಾತ್ರ ಇರಿಸಲಾಗುತ್ತದೆ. ಇವುಗಳನ್ನು ಎಂದಿಗೂ ಡಿಸ್ಕ್ ಅಥವಾ ಶಾಶ್ವತ ಡೇಟಾಬೇಸ್‌ಗಳಲ್ಲಿ ಉಳಿಸಲಾಗುವುದಿಲ್ಲ.'
              : language === 'te'
              ? 'సంక్షేమ అర్హతను నిర్ణయించడానికి అన్ని వివరాలు యాక్టివ్ సెషన్ మెమరీలో మాత్రమే ఉంచబడతాయి. అవి ఎప్పుడూ డిస్క్ లేదా శాశ్వత డేటాబేస్లలో నిల్వ చేయబడవు.'
              : 'All attributes are held exclusively in active session memory to deterministically evaluate welfare eligibility. They are never saved to disk or permanent databases.'}
          </p>
        </div>

        {/* Action Button */}
        <div className="pt-1">
          <button
            type="button"
            onClick={() => {
              setHasConfirmedProfile(true);
              navigate('/my-schemes');
            }}
            className="w-full bg-forest hover:bg-forest-deep text-white font-bold py-3.5 px-6 rounded-2xl shadow-md flex items-center justify-center gap-2 text-sm transition-transform active:scale-98 min-h-[50px]"
          >
            <span>
              {language === 'hi'
                ? 'सभी मेल खाती योजनाएं देखें'
                : language === 'kn'
                ? 'ಹೊಂದಾಣಿಕೆಯಾಗುವ ಎಲ್ಲಾ ಯೋಜನೆಗಳನ್ನು ಅನ್ವೇಷಿಸಿ'
                : language === 'te'
                ? 'సరిపోలే అన్ని పథకాలను అన్వేషించండి'
                : 'Explore All Matching Schemes'}
            </span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>

      {/* SINGLE ATTRIBUTE EDIT MODAL */}
      {activeEditField && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm animate-fade-in"
          onClick={() => setActiveEditField(null)}
        >
          <div
            className="bg-surface rounded-2xl shadow-2xl border border-sand w-full max-w-md overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-sand bg-canvas">
              <h3 className="font-heading font-bold text-base text-ink">
                {language === 'hi'
                  ? 'संपादित करें: '
                  : language === 'kn'
                  ? 'ಸಂಪಾದಿಸಿ: '
                  : language === 'te'
                  ? 'సవరించు: '
                  : 'Edit '}
                {attributeCards.find((c) => c.key === activeEditField)?.label}
              </h3>
              <button
                type="button"
                onClick={() => setActiveEditField(null)}
                aria-label="Close"
                className="p-1 rounded-full hover:bg-sand/40 text-ink/70 hover:text-ink transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSingleField} className="p-5 space-y-4">
              {validationError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold">
                  {validationError}
                </div>
              )}
              {saveSuccessMsg && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-1.5">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>{saveSuccessMsg}</span>
                </div>
              )}

              {/* Dynamic input by field type */}
              {activeEditField === 'age' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'वर्षों में आयु (0 - 120)'
                      : language === 'kn'
                      ? 'ವರ್ಷಗಳಲ್ಲಿ ವಯಸ್ಸು (0 - 120)'
                      : language === 'te'
                      ? 'సంవత్సరాలలో వయస్సు (0 - 120)'
                      : 'Age in years (0 - 120)'}
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="120"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder="e.g. 35"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                    autoFocus
                  />
                </div>
              )}

              {activeEditField === 'gender' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi' ? 'लिंग' : language === 'kn' ? 'ಲಿಂಗ' : language === 'te' ? 'లింగం' : 'Gender'}
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {(LOCALIZED_GENDERS_MAP[language] || LOCALIZED_GENDERS_MAP.en).map((g) => (
                      <button
                        type="button"
                        key={g.key}
                        onClick={() => setEditValue(g.key)}
                        className={`p-2.5 rounded-xl border text-center text-xs font-bold transition-all ${
                          String(editValue).toLowerCase() === g.key.toLowerCase()
                            ? 'bg-forest text-white border-forest shadow-sm'
                            : 'bg-canvas text-ink border-sand hover:border-forest/40'
                        }`}
                      >
                        {g.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {activeEditField === 'state' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'राज्य / केंद्र शासित प्रदेश'
                      : language === 'kn'
                      ? 'ರಾಜ್ಯ / ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ'
                      : language === 'te'
                      ? 'రాష్ట్రం / కేంద్రపాలిత ప్రాంతం'
                      : 'State / Union Territory'}
                  </label>
                  <select
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                  >
                    <option value="">
                      {language === 'hi'
                        ? 'राज्य / केंद्र शासित प्रदेश चुनें'
                        : language === 'kn'
                        ? 'ರಾಜ್ಯ/ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ ಆಯ್ಕೆಮಾಡಿ'
                        : language === 'te'
                        ? 'రాష్ట్రం/కేంద్రపాలిత ప్రాంతాన్ని ఎంచుకోండి'
                        : 'Select State/UT'}
                    </option>
                    {INDIAN_STATES_AND_UTS.map((st) => (
                      <option key={st.code} value={st.name}>
                        {st.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {activeEditField === 'occupation' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'मुख्य व्यवसाय'
                      : language === 'kn'
                      ? 'ಮುಖ್ಯ ಕಸುಬು / ಉದ್ಯೋಗ'
                      : language === 'te'
                      ? 'ప్రధాన వృత్తి'
                      : 'Primary Occupation'}
                  </label>
                  <select
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                  >
                    <option value="">
                      {language === 'hi'
                        ? 'व्यवसाय चुनें'
                        : language === 'kn'
                        ? 'ಉದ್ಯೋಗ ಆಯ್ಕೆಮಾಡಿ'
                        : language === 'te'
                        ? 'వృత్తిని ఎంచుకోండి'
                        : 'Select Occupation'}
                    </option>
                    {(LOCALIZED_OCCUPATION_MAP[language] || LOCALIZED_OCCUPATION_MAP.en).map((occ) => (
                      <option key={occ.key} value={occ.key}>
                        {occ.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {activeEditField === 'farmerType' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'कृषक / गतिविधि का प्रकार'
                      : language === 'kn'
                      ? 'ಕೃಷಿಕ / ಚಟುವಟಿಕೆ ಪ್ರಕಾರ'
                      : language === 'te'
                      ? 'సాగుదారు / కార్యకలాపం రకం'
                      : 'Cultivator / Activity Type'}
                  </label>
                  <div className="space-y-2">
                    {(LOCALIZED_FARMER_TYPES_MAP[language] || LOCALIZED_FARMER_TYPES_MAP.en).map((ft) => (
                      <button
                        type="button"
                        key={ft.key}
                        onClick={() => setEditValue(ft.key)}
                        className={`w-full p-2.5 rounded-xl border text-left text-xs font-semibold flex items-center justify-between ${
                          editValue === ft.key
                            ? 'bg-forest text-white border-forest shadow-sm'
                            : 'bg-canvas text-ink border-sand hover:border-forest/40'
                        }`}
                      >
                        <span>{ft.label}</span>
                        {editValue === ft.key && <Check className="w-3.5 h-3.5" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {activeEditField === 'annualIncome' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'वार्षिक पारिवारिक आय (₹)'
                      : language === 'kn'
                      ? 'ವಾರ್ಷಿಕ ಕುಟುಂಬ ಆದಾಯ (₹)'
                      : language === 'te'
                      ? 'వార్షిక కుటుంబ ఆదాయం (₹)'
                      : 'Annual Family Income (₹)'}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder="e.g. 150000"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                    autoFocus
                  />
                </div>
              )}

              {activeEditField === 'monthlyPension' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'मासिक पेंशन राशि (₹)'
                      : language === 'kn'
                      ? 'ಮಾಸಿಕ ಪಿಂಚಣಿ ಮೊತ್ತ (₹)'
                      : language === 'te'
                      ? 'నెలవారీ పెన్షన్ మొత్తం (₹)'
                      : 'Monthly Pension Amount (₹)'}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder="e.g. 12000 (0 if no pension)"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                    autoFocus
                  />
                </div>
              )}

              {activeEditField === 'landholdingHectares' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'हेक्टेयर में भूमि का आकार'
                      : language === 'kn'
                      ? 'ಹೆಕ್ಟೇರ್‌ಗಳಲ್ಲಿ ಕೃಷಿ ಭೂಮಿ ವಿಸ್ತೀರ್ಣ'
                      : language === 'te'
                      ? 'హెక్టార్లలో వ్యవసాయ భూమి పరిమాణం'
                      : 'Landholding in Hectares'}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder="e.g. 1.5"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                    autoFocus
                  />
                </div>
              )}

              {(activeEditField === 'isBankDefaulter' ||
                activeEditField === 'hasBPLCard' ||
                activeEditField === 'paysIncomeTax' ||
                activeEditField === 'hasRegularGovtJob' ||
                activeEditField === 'ownsPuccaHouse' ||
                activeEditField === 'isDifferentlyAbled' ||
                activeEditField === 'ownsAgriculturalLand') && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-2">
                    {activeEditField === 'paysIncomeTax' &&
                      (language === 'hi'
                        ? 'क्या आपने या आपके परिवार ने पिछले आकलन वर्ष में आयकर का भुगतान किया है?'
                        : language === 'kn'
                        ? 'ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬವು ಕಳೆದ ವರ್ಷ ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸಿದ್ದೀರಾ?'
                        : language === 'te'
                        ? 'మీరు లేదా మీ కుటుంబం గత అసెస్‌మెంట్ సంవత్సరంలో ఆదాయపు పన్ను చెల్లించారా?'
                        : 'Did you or your family pay income tax in the last assessment year?')}
                    {activeEditField === 'hasRegularGovtJob' &&
                      (language === 'hi'
                        ? 'क्या आपके परिवार का कोई सदस्य नियमित सरकारी या पीएसयू कर्मचारी है?'
                        : language === 'kn'
                        ? 'ನಿಮ್ಮ ಕುಟುಂಬದ ಯಾರಾದರೂ ಕಾಯಂ ಸರ್ಕಾರಿ ಅಥವಾ ಪಿಎಸ್‌ಯು ನೌಕರರೇ?'
                        : language === 'te'
                        ? 'మీ కుటుంబంలో ఎవరైనా రెగ్యులర్ ప్రభుత్వ లేదా పిఎస్‌యు ఉద్యోగా?'
                        : 'Is any member of your family a regular Government or PSU employee?')}
                    {activeEditField === 'ownsPuccaHouse' &&
                      (language === 'hi'
                        ? 'क्या आपके पास स्वयं का पक्का स्थायी आवासीय मकान है?'
                        : language === 'kn'
                        ? 'ನಿಮ್ಮ ಸ್ವಂತ ಪಕ್ಕಾ ಶಾಶ್ವತ ವಸತಿ ಮನೆ ಇದೆಯೇ?'
                        : language === 'te'
                        ? 'మీకు సొంతంగా పక్కా శాశ్వత నివాస గృహం ఉందా?'
                        : 'Do you own a pucca permanent residential house?')}
                    {activeEditField === 'isDifferentlyAbled' &&
                      (language === 'hi'
                        ? 'क्या आप 40% या अधिक दिव्यांगता वाले व्यक्ति (दिव्यांगजन) हैं?'
                        : language === 'kn'
                        ? 'ನೀವು ಮಾನದಂಡದ ಅಂಗವೈಕಲ್ಯ ಹೊಂದಿರುವ ವಿಶೇಷ ಚೇತನರೇ (PwD)?'
                        : language === 'te'
                        ? 'మీరు బెంచ్‌మార్క్ వైకల్యం కలిగిన దివ్యాంగులా (PwD)?'
                        : 'Are you a differently abled person (PwD) with benchmark disability?')}
                    {activeEditField === 'ownsAgriculturalLand' &&
                      (language === 'hi'
                        ? 'क्या आपके या आपके परिवार के पास कृषि योग्य भूमि है?'
                        : language === 'kn'
                        ? 'ನಿಮ್ಮ ಬಳಿ ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಬಳಿ ಕೃಷಿ ಭೂಮಿ ಇದೆಯೇ?'
                        : language === 'te'
                        ? 'మీకు లేదా మీ కుటుంబానికి వ్యవసాయ భూమి ఉందా?'
                        : 'Do you or your household own agricultural land?')}
                    {activeEditField === 'isBankDefaulter' &&
                      (language === 'hi'
                        ? 'क्या आपके पास कोई अनिस्तारित संस्थागत बैंक ऋण डिफ़ॉल्ट है?'
                        : language === 'kn'
                        ? 'ನಿಮ್ಮ ಬಳಿ ಇತ್ಯರ್ಥವಾಗದ ಸಾಂಸ್ಥಿಕ ಬ್ಯಾಂಕ್ ಸಾಲ ಬಾಕಿ ಇದೆಯೇ?'
                        : language === 'te'
                        ? 'మీ వద్ద పరిష్కారం కాని సంస్థాగత బ్యాంకు రుణం డిఫాల్ట్ ఉందా?'
                        : 'Do you have an unresolved institutional bank loan default?')}
                    {activeEditField === 'hasBPLCard' &&
                      (language === 'hi'
                        ? 'क्या आपके पास सक्रिय बीपीएल या राशन कार्ड है?'
                        : language === 'kn'
                        ? 'ನಿಮ್ಮ ಬಳಿ ಸಕ್ರಿಯ ಬಿಪಿಎಲ್ ಅಥವಾ ರೇಷನ್ ಕಾರ್ಡ್ ಇದೆಯೇ?'
                        : language === 'te'
                        ? 'మీ వద్ద క్రియాశీల బిపిఎల్ లేదా రేషన్ కార్డు ఉందా?'
                        : 'Do you possess an active BPL or Ration Card?')}
                  </label>
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => setEditValue(true)}
                      className={`p-3 rounded-xl border text-center text-xs font-bold transition-all ${
                        editValue === true
                          ? 'bg-forest text-white border-forest shadow-sm'
                          : 'bg-canvas text-ink border-sand hover:border-forest/40'
                      }`}
                    >
                      {language === 'hi' ? 'हाँ (Yes)' : language === 'kn' ? 'ಹೌದು (Yes)' : language === 'te' ? 'అవును (Yes)' : 'Yes'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditValue(false)}
                      className={`p-3 rounded-xl border text-center text-xs font-bold transition-all ${
                        editValue === false
                          ? 'bg-forest text-white border-forest shadow-sm'
                          : 'bg-canvas text-ink border-sand hover:border-forest/40'
                      }`}
                    >
                      {language === 'hi' ? 'नहीं (No)' : language === 'kn' ? 'ಇಲ್ಲ (No)' : language === 'te' ? 'కాదు (No)' : 'No'}
                    </button>
                  </div>
                </div>
              )}

              {activeEditField === 'socialCategory' && (
                <div>
                  <label className="block text-xs font-bold text-ink mb-1.5">
                    {language === 'hi'
                      ? 'सामाजिक श्रेणी'
                      : language === 'kn'
                      ? 'ಸಾಮಾಜಿಕ ವರ್ಗ'
                      : language === 'te'
                      ? 'సామాజిక వర్గం'
                      : 'Social Category'}
                  </label>
                  <select
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
                  >
                    <option value="">
                      {language === 'hi'
                        ? 'श्रेणी चुनें'
                        : language === 'kn'
                        ? 'ವರ್ಗ ಆಯ್ಕೆಮಾಡಿ'
                        : language === 'te'
                        ? 'వర్గాన్ని ఎంచుకోండి'
                        : 'Select Category'}
                    </option>
                    {(LOCALIZED_CASTES_MAP[language] || LOCALIZED_CASTES_MAP.en).map((cat) => (
                      <option key={cat.key} value={cat.key}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Save / Cancel buttons */}
              <div className="flex items-center gap-2 pt-3 border-t border-sand">
                <button
                  type="button"
                  onClick={() => setActiveEditField(null)}
                  className="flex-1 py-2.5 px-4 rounded-xl border border-sand bg-canvas text-ink text-xs font-semibold hover:bg-sand/30 transition-colors"
                >
                  {language === 'hi'
                    ? 'रद्द करें'
                    : language === 'kn'
                    ? 'ರದ್ದುಮಾಡಿ'
                    : language === 'te'
                    ? 'రద్దు చేయి'
                    : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 px-4 rounded-xl bg-forest hover:bg-forest-deep text-white text-xs font-bold shadow-sm transition-transform active:scale-95"
                >
                  {language === 'hi'
                    ? 'विवरण सुरक्षित करें'
                    : language === 'kn'
                    ? 'ಉಳಿಸಿ'
                    : language === 'te'
                    ? 'భద్రపరచు'
                    : 'Save Attribute'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <BottomNav />
    </div>
  );
};
