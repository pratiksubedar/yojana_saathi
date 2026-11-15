import type { Scheme, Language } from '../types/index.ts';

export interface LocalizedSchemeContent {
  nativeName: Record<Language, string>;
  benefitHighlight: Record<Language, string>;
  description: Record<Language, string>;
  matchingCriteria: Record<Language, string[]>;
  failedCriteria?: Record<Language, string[]>;
  missingCriteria?: Record<Language, string[]>;
}

export const MOCK_SCHEMES: Scheme[] = [
  {
    id: 'pm-kisan',
    name: 'PM-KISAN Samman Nidhi',
    nativeName: 'प्रधानमंत्री किसान सम्मान निधि',
    ministry: 'Ministry of Agriculture & Farmers Welfare',
    category: 'agriculture',
    benefit: '₹6,000 per year',
    benefitHighlight: '₹6,000 / year via Direct Benefit Transfer (3 equal installments of ₹2,000)',
    status: 'eligible',
    matchScore: 98,
    description: 'An income support scheme providing ₹6,000 per year in three equal 4-monthly installments directly into bank accounts of all landholding farmer families.',
    matchingCriteria: [
      'Small or marginal farmer landholding (< 2.0 Hectares)',
      'Cultivable land records verified',
      'Valid Aadhaar-linked active bank account'
    ],
    missingCriteria: [],
    failedCriteria: [],
    criteriaList: [
      'Farmer families with cultivable landholding up to 2 hectares in their name',
      'Citizen of India with valid land registry records (Khatauni/Khasra/RTC)',
      'Must complete eKYC on the PM-KISAN portal'
    ],
    exclusions: [
      'Institutional landholders',
      'Farmer families holding constitutional posts or serving as Govt employees',
      'All persons who paid Income Tax in last assessment year',
      'Professionals like Doctors, Engineers, Lawyers, Chartered Accountants'
    ],
    requiredDocuments: [
      { id: 'doc-1', name: 'Land Ownership Document (RTC / Khatauni / Pattadar Passbook)', required: true, description: 'Updated state revenue records proving cultivable land.' },
      { id: 'doc-2', name: 'Aadhaar Card Copy', required: true, description: 'Mandatory identification document with linked mobile number.' },
      { id: 'doc-3', name: 'Active Bank Account Passbook', required: true, description: 'Bank passbook with clear IFSC code and Aadhaar-seeded NPCI mapping.' },
      { id: 'doc-4', name: 'Passport Size Photograph', required: false, description: 'Two recent color passport photos for physical CSC filing.' }
    ],
    applicationSteps: [
      'Visit official portal https://pmkisan.gov.in or nearest Common Service Centre (CSC) / Grama One / Ward Sachivalayam',
      'Click on "Farmers Corner" -> "New Farmer Registration"',
      'Enter Rural/Urban status, Aadhaar Number, and mobile number to receive OTP',
      'Fill state, district, sub-district, block, village and land registry details',
      'Upload land ownership PDF and bank passbook proof, then submit and record Registration Number'
    ],
    officialUrl: 'https://pmkisan.gov.in',
    portalName: 'PM-KISAN Portal',
    cscApplicable: true,
    lastUpdated: '15 Jan 2026',
    verifiedOfficial: true
  },
  {
    id: 'pm-jay',
    name: 'Ayushman Bharat PM-JAY',
    nativeName: 'आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना',
    ministry: 'Ministry of Health & Family Welfare / NHA',
    category: 'healthcare',
    benefit: '₹5,00,000 per family/year',
    benefitHighlight: '₹5 Lakh cashless health cover for secondary & tertiary hospital care',
    status: 'eligible',
    matchScore: 95,
    description: 'The world’s largest health assurance scheme providing a health cover of ₹5 lakh per family per year for secondary and tertiary care hospitalization to over 12 crore poor and vulnerable families.',
    matchingCriteria: [
      'Identified in SECC 2011 deprivation criteria (Rural)',
      'Annual household income below ₹2,50,000',
      'Family resides in designated rural block'
    ],
    missingCriteria: [],
    failedCriteria: [],
    criteriaList: [
      'Households listed under SECC 2011 rural deprivation criteria D1 to D7',
      'Families having active Rashtriya Swasthya Bima Yojana (RSBY) enrolment',
      'All senior citizens aged 70+ irrespective of income'
    ],
    exclusions: [
      'Families owning motorized 2/3/4-wheelers or mechanized fishing boats',
      'Government employees or households with landholding above ceiling limit',
      'Households with any member paying income tax'
    ],
    requiredDocuments: [
      { id: 'doc-jay-1', name: 'Aadhaar Card', required: true, description: 'Primary ID for biometric e-KYC.' },
      { id: 'doc-jay-2', name: 'Ration Card (NFSA / BPL)', required: true, description: 'State-issued family ration card to verify family composition.' }
    ],
    applicationSteps: [
      'Visit https://beneficiary.nha.gov.in or any empaneled public/private hospital Ayushman Mitra desk',
      'Search family using Aadhaar number or Ration Card number',
      'Complete Aadhaar OTP or fingerprint authentication',
      'Download and print the Ayushman Card instantly'
    ],
    officialUrl: 'https://beneficiary.nha.gov.in',
    portalName: 'NHA Beneficiary Portal',
    cscApplicable: true,
    lastUpdated: '01 Feb 2026',
    verifiedOfficial: true
  },
  {
    id: 'pmay-g',
    name: 'PMAY-G (Gramin Housing Scheme)',
    nativeName: 'प्रधानमंत्री आवास योजना - ग्रामीण',
    ministry: 'Ministry of Rural Development',
    category: 'housing',
    benefit: '₹1,20,000 grant + 90 days MGNREGA wages',
    benefitHighlight: '₹1.20 Lakh financial assistance for pucca house construction in plain areas',
    status: 'possibly_eligible',
    matchScore: 78,
    description: 'Provides financial assistance to homeless and households living in kutcha or dilapidated houses in rural areas to construct a permanent pucca house with basic amenities.',
    matchingCriteria: [
      'Rural resident without existing pucca house',
      'Belongs to OBC/BPL social category'
    ],
    missingCriteria: [
      'Gram Panchayat Awaas+ priority list inclusion verification needed',
      'Kutcha house verification by Village Officer required'
    ],
    failedCriteria: [],
    criteriaList: [
      'Houseless households or households living in zero, one or two room kutcha houses',
      'Included in SECC 2011 or Awaas+ survey list',
      'Must possess land or be allotted land by state govt'
    ],
    exclusions: [
      'Motorized vehicle or mechanized agricultural equipment owners',
      'Any member earning more than ₹15,000 per month',
      'Families possessing 5 acres or more of irrigated land'
    ],
    requiredDocuments: [
      { id: 'doc-pmay-1', name: 'Aadhaar Card of adult members', required: true, description: 'For biometric Aadhaar seeding.' },
      { id: 'doc-pmay-2', name: 'MGNREGA Job Card', required: true, description: 'To claim 90-95 days unskilled labor wage support.' },
      { id: 'doc-pmay-3', name: 'Bank Account Linked with Aadhaar', required: true, description: 'For direct stage-wise DBT release.' },
      { id: 'doc-pmay-4', name: 'Land Title / Gram Sabha Allotment Letter', required: true, description: 'Proof of site possession.' }
    ],
    applicationSteps: [
      'Contact your Gram Panchayat Secretary (Sachiv/PDO) or Village Employment Assistant',
      'Verify inclusion on the AwaasSoft beneficiary priority list',
      'Geo-tagged photo of existing kutcha house taken by village surveyor',
      'Sanction order issued by Block Development Office (BDO) directly'
    ],
    officialUrl: 'https://pmayg.nic.in',
    portalName: 'PMAY-G AwaasSoft',
    cscApplicable: true,
    lastUpdated: '10 Jan 2026',
    verifiedOfficial: true
  },
  {
    id: 'pm-svanidhi',
    name: 'PM SVANidhi (Street Vendors Scheme)',
    nativeName: 'पीएम स्वनिधि योजना',
    ministry: 'Ministry of Housing & Urban Affairs',
    category: 'employment',
    benefit: 'Collateral-free working capital up to ₹50,000',
    benefitHighlight: 'Initial ₹10,000 loan -> ₹20,000 -> ₹50,000 on timely repayment with 7% interest subsidy',
    status: 'possibly_eligible',
    matchScore: 70,
    description: 'A special micro-credit facility providing street vendors affordable working capital loans to resume their livelihoods post-pandemic, incentivizing digital transactions with monthly cashback.',
    matchingCriteria: [
      'Age between 18 and 60 years',
      'Self-employed informal vendor occupation'
    ],
    missingCriteria: [
      'Urban Local Body (ULB) Vending Certificate or Letter of Recommendation (LoR)'
    ],
    failedCriteria: [],
    criteriaList: [
      'Street vendors vending in urban areas on or before March 24, 2020',
      'Vendors possessing Certificate of Vending / ID card issued by Urban Local Body',
      'Vendors from surrounding peri-urban/rural areas vending in geographical limits of ULB'
    ],
    exclusions: [
      'Borrowers with willful default history in commercial banks',
      'Non-vendors or established brick-and-mortar storefront owners'
    ],
    requiredDocuments: [
      { id: 'doc-sva-1', name: 'Aadhaar Card', required: true, description: 'Identity verification.' },
      { id: 'doc-sva-2', name: 'Vending Certificate or ULB Recommendation Letter', required: true, description: 'Mandatory proof of street vending.' },
      { id: 'doc-sva-3', name: 'Bank Account Details', required: true, description: 'Active savings account for loan disbursement.' }
    ],
    applicationSteps: [
      'Apply online on https://pmsvanidhi.mohua.gov.in or through lending bank branch',
      'Select eligible Lending Institution (Public/Private Bank, MFI, or SHG)',
      'Upload KYC documents and Certificate of Vending',
      'Loan disbursed within 15-30 days upon digital approval'
    ],
    officialUrl: 'https://pmsvanidhi.mohua.gov.in',
    portalName: 'PM SVANidhi Portal',
    cscApplicable: true,
    lastUpdated: '20 Jan 2026',
    verifiedOfficial: true
  },
  {
    id: 'pm-kmy',
    name: 'PM Kisan Maan-Dhan Yojana (PM-KMY)',
    nativeName: 'प्रधानमंत्री किसान मान-धन योजना',
    ministry: 'Ministry of Agriculture & Farmers Welfare',
    category: 'agriculture',
    benefit: '₹3,000 monthly pension after age 60',
    benefitHighlight: 'Assured ₹3,000/month lifelong social security pension with 50% govt co-contribution',
    status: 'eligible',
    matchScore: 92,
    description: 'An old-age social security pension scheme for small and marginal farmers between the age group of 18 to 40 years, guaranteeing a monthly pension of ₹3,000 upon reaching 60 years.',
    matchingCriteria: [
      'Age is 38 years (within 18-40 age window)',
      'Cultivable landholding is below 2.0 hectares',
      'Small and marginal farmer category'
    ],
    missingCriteria: [],
    failedCriteria: [],
    criteriaList: [
      'Small and Marginal Farmers having cultivable land up to 2 hectares as per state land records',
      'Entry age between 18 and 40 years',
      'Monthly contribution between ₹55 and ₹200 (matched 1:1 by Central Govt)'
    ],
    exclusions: [
      'Farmers covered under other social security schemes like NPS, ESIC, EPFO',
      'Farmers who have opted for PM Shram Yogi Maan-Dhan Yojana',
      'Income Tax payers and institutional landholders'
    ],
    requiredDocuments: [
      { id: 'doc-kmy-1', name: 'Aadhaar Card', required: true, description: 'Primary ID.' },
      { id: 'doc-kmy-2', name: 'Land Record Copy (RTC/Khatauni)', required: true, description: 'Proof of landholding size.' },
      { id: 'doc-kmy-3', name: 'Savings Bank Account & Auto-Debit Mandate', required: true, description: 'For monthly auto-debit contribution.' }
    ],
    applicationSteps: [
      'Visit nearest Common Service Centre (CSC) / Grama One / Ward Sachivalayam',
      'Provide Aadhaar, Land Record, and Savings Bank details',
      'Auto-debit mandate signed and biometric authentication completed',
      'Instant issuance of Kisan Pension Card'
    ],
    officialUrl: 'https://maandhan.in',
    portalName: 'Maan-Dhan Central Portal',
    cscApplicable: true,
    lastUpdated: '05 Jan 2026',
    verifiedOfficial: true
  },
  {
    id: 'pmmvy',
    name: 'Pradhan Mantri Matru Vandana Yojana (PMMVY)',
    nativeName: 'प्रधानमंत्री मातृ वंदना योजना',
    ministry: 'Ministry of Women and Child Development',
    category: 'social_welfare',
    benefit: '₹5,00,000 maternity cash benefit',
    benefitHighlight: 'Conditional cash incentive for pregnant and lactating mothers for first and second girl child',
    status: 'not_eligible',
    matchScore: 25,
    description: 'A Centrally Sponsored scheme providing conditional maternity benefit to pregnant women and lactating mothers for improved health and nutrition during pregnancy and childbirth.',
    matchingCriteria: [],
    missingCriteria: [],
    failedCriteria: [
      'Beneficiary gender requirement: Must be a pregnant woman or lactating mother (Current profile: Male)',
      'Applicable only for female applicants enrolled at Anganwadi / Health Center'
    ],
    criteriaList: [
      'Pregnant women and lactating mothers (PW&LM) who have conceived their 1st or 2nd child (if 2nd child is a girl child)',
      'Must register pregnancy at nearest Anganwadi Centre (AWC) or approved Health Facility'
    ],
    exclusions: [
      'Regular employees of Central Government, State Governments or PSUs',
      'Those receiving similar maternity benefits under any other operational law',
      'Male applicants'
    ],
    requiredDocuments: [
      { id: 'doc-mat-1', name: 'Mother Child Protection (MCP) Card', required: true, description: 'Anganwadi registration record.' },
      { id: 'doc-mat-2', name: 'Aadhaar Card of Mother and Husband', required: true, description: 'Identity proof.' },
      { id: 'doc-mat-3', name: 'Bank Account in Mother\'s Name', required: true, description: 'Aadhaar-seeded single account.' }
    ],
    applicationSteps: [
      'Register at the local Anganwadi Centre within 150 days of Last Menstrual Period (LMP)',
      'Submit Form 1A along with MCP card copy and Aadhaar',
      'Receive first installment upon early ANC registration',
      'Receive subsequent installments upon institutional delivery and infant vaccinations'
    ],
    officialUrl: 'https://pmmvy.wcd.gov.in',
    portalName: 'PMMVY Soft Portal',
    cscApplicable: true,
    lastUpdated: '12 Jan 2026',
    verifiedOfficial: true
  },
  {
    id: 'pm-kusum',
    name: 'PM-KUSUM (Solar Agriculture Pump Scheme)',
    nativeName: 'पीएम-कुसुम सौर कृषि पंप योजना',
    ministry: 'Ministry of New & Renewable Energy',
    category: 'agriculture',
    benefit: 'Up to 60% subsidy on solar pump installation',
    benefitHighlight: '60% capital subsidy on standalone solar pumps (3HP to 7.5HP) with 30% bank loan',
    status: 'eligible',
    matchScore: 88,
    description: 'Enables farmers, farmer groups, and cooperatives to set up standalone solar agricultural pumps and solarize existing grid-connected agriculture pumps for reliable irrigation and extra power sale.',
    matchingCriteria: [
      'Possesses agricultural land requiring irrigation',
      'Rural location in power deficient agricultural feeder zone'
    ],
    missingCriteria: [],
    failedCriteria: [],
    criteriaList: [
      'Individual farmers, Water User Associations, Primary Agriculture Credit Societies (PACS)',
      'Possessing land with borewell or surface water source'
    ],
    exclusions: [
      'Farmers who have already availed solar pump subsidy under state schemes within past 5 years'
    ],
    requiredDocuments: [
      { id: 'doc-kusum-1', name: 'Land Record Document (RTC/Khatauni)', required: true, description: 'Proof of agricultural land.' },
      { id: 'doc-kusum-2', name: 'Aadhaar Card', required: true, description: 'Beneficiary ID.' },
      { id: 'doc-kusum-3', name: 'Bank Account Passbook', required: true, description: 'For processing farmer contribution and subsidy.' }
    ],
    applicationSteps: [
      'Visit State Renewable Energy Development Agency portal (e.g. KREDL in Karnataka / NREDCAP in AP / TSREDCO in Telangana)',
      'Select Component B (Standalone solar pump)',
      'Pay farmer contribution (approx 10%) online',
      'Site survey and solar pump installation by authorized vendor within 90 days'
    ],
    officialUrl: 'https://pmkusum.mnre.gov.in',
    portalName: 'PM-KUSUM MNRE Portal',
    cscApplicable: true,
    lastUpdated: '08 Jan 2026',
    verifiedOfficial: true
  }
];

// Multilingual translations for Scheme attributes in English, Hindi, Kannada, Telugu
const SCHEME_TRANSLATIONS: Record<string, LocalizedSchemeContent> = {
  'pm-kisan': {
    nativeName: {
      en: 'PM-KISAN Samman Nidhi',
      hi: 'प्रधानमंत्री किसान सम्मान निधि',
      kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ',
      te: 'ప్రధానమంత్రి కిసాన్ సమ్మాన్ నిధి',
    },
    benefitHighlight: {
      en: '₹6,000 / year via Direct Benefit Transfer (3 equal installments of ₹2,000)',
      hi: '₹6,000 / वर्ष Direct Benefit Transfer (3 समान किस्तों में ₹2,000)',
      kn: 'ನೇರ ನಗದು ವರ್ಗಾವಣೆ (DBT) ಮೂಲಕ ವಾರ್ಷಿಕ ₹6,000 (ತಲಾ ₹2,000 ರಂತೆ 3 ಕಂತುಗಳಲ್ಲಿ)',
      te: 'ప్రత్యక్ష నగదు బదిలీ (DBT) ద్వారా సంవత్సరానికి ₹6,000 (₹2,000 చొప్పున 3 విడతల్లో)',
    },
    description: {
      en: 'An income support scheme providing ₹6,000 per year directly into bank accounts of landholding farmer families.',
      hi: 'पात्र किसान परिवारों को प्रति वर्ष ₹6,000 की वित्तीय सहायता सीधे बैंक खाते में प्रदान करने वाली केंद्रीय योजना।',
      kn: 'ಅರ್ಹ ಭೂಮಾಲೀಕ ರೈತ ಕುಟುಂಬಗಳ ಬ್ಯಾಂಕ್ ಖಾತೆಗೆ ನೇರವಾಗಿ ವಾರ್ಷಿಕ ₹6,000 ಆದಾಯ ಬೆಂಬಲ ನೀಡುವ ಕೇಂದ್ರ ಸರ್ಕಾರದ ಮಹತ್ವದ ಯೋಜನೆ.',
      te: 'అర్హులైన భూమి ఉన్న రైతు కుటుంబాల బ్యాంక్ ఖాతాల్లో నేరుగా ఏటా ₹6,000 ఆర్థిక సహాయం అందించే కేంద్ర పథకం.',
    },
    matchingCriteria: {
      en: [
        'Small or marginal farmer landholding (< 2.0 Hectares)',
        'Valid cultivable land revenue records (RTC/Khatauni)',
        'Active Aadhaar-linked bank account'
      ],
      hi: [
        'लघु अथवा सीमांत किसान (< 2.0 हेक्टेयर ज़मीन)',
        'कृषि योग्य भूमि के वैध राजस्व रिकॉर्ड',
        'आधार से जुड़ा सक्रिय बैंक खाता'
      ],
      kn: [
        'ಸಣ್ಣ ಅಥವಾ ಅತಿ ಸಣ್ಣ ರೈತರ ಭೂಮಿ (< 2.0 ಹೆಕ್ಟೇರ್)',
        'ಮಾನ್ಯ ಕೃಷಿ ಭೂಮಿಯ ಕಂದಾಯ ದಾಖಲೆ (ಪಹಣಿ/RTC)',
        'ಆಧಾರ್ ಜೋಡಣೆಯಾದ ಸಕ್ರಿಯ ಬ್ಯಾಂಕ್ ಖಾತೆ'
      ],
      te: [
        'చిన్న లేదా సన్నకారు రైతు భూకమతం (< 2.0 హెక్టార్లు)',
        'చెల్లుబాటు అయ్యే వ్యవసాయ భూమి పట్టాదారు పాస్‌బుక్',
        'ఆధార్‌తో లింక్ చేయబడిన బ్యాంక్ ఖాతా'
      ]
    }
  },
  'pm-jay': {
    nativeName: {
      en: 'Ayushman Bharat PM-JAY',
      hi: 'आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना',
      kn: 'ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಪ್ರಧಾನಮಂತ್ರಿ ಜನ ಆರೋಗ್ಯ ಯೋಜನೆ',
      te: 'ఆయుష్మాన్ భారత్ ప్రధానమంత్రి జన ఆరోగ్య యోజన',
    },
    benefitHighlight: {
      en: '₹5 Lakh cashless health cover per family/year for secondary & tertiary care',
      hi: 'प्रति परिवार प्रति वर्ष ₹5 लाख तक का कैशलेस स्वास्थ्य सुरक्षा कवर',
      kn: 'ಪ್ರತಿ ಕುಟುಂಬಕ್ಕೆ ವಾರ್ಷಿಕ ₹5 ಲಕ್ಷದವರೆಗೆ ನಗದುರಹಿತ ಉಚಿತ ಆಸ್ಪತ್ರೆ ಚಿಕಿತ್ಸೆ',
      te: 'ప్రతి కుటుంబానికి సంవత్సరానికి ₹5 లక్షల వరకు ఉచిత నగదు రహిత ఆసుపత్రి చికిత్స',
    },
    description: {
      en: 'World’s largest health assurance scheme providing ₹5 lakh cashless hospitalization cover to vulnerable families.',
      hi: 'द्वितीयक और तृतीयक स्तर के अस्पताल में भर्ती होने पर 12 करोड़ से अधिक गरीब परिवारों को ₹5 लाख का मुफ्त इलाज।',
      kn: 'ಬಡ ಮತ್ತು ದುರ್ಬಲ ಕುಟುಂಬಗಳಿಗೆ ಆಸ್ಪತ್ರೆ ದಾಖಲಾತಿಯಲ್ಲಿ ₹5 ಲಕ್ಷದವರೆಗೆ ಸಂಪೂರ್ಣ ಉಚಿತ ಚಿಕಿತ್ಸೆ ಒದಗಿಸುವ ಬೃಹತ್ ಆರೋಗ್ಯ ರಕ್ಷಣಾ ಯೋಜನೆ.',
      te: 'పేద మరియు బలహీన కుటుంబాలకు ఆసుపత్రిలో చేరినప్పుడు ₹5 లక్షల వరకు ఉచిత చికిత్సను అందించే ప్రపంచంలోనే అతిపెద్ద ఆరోగ్య పథకం.',
    },
    matchingCriteria: {
      en: [
        'Identified in SECC 2011 deprivation criteria',
        'Household income below eligible threshold',
        'Valid NFSA / state BPL ration card'
      ],
      hi: [
        'SECC 2011 ग्रामीण वंचना सूची में शामिल परिवार',
        'वार्षिक पारिवारिक आय ₹2.5 लाख से कम',
        'राशन कार्ड धारक'
      ],
      kn: [
        'SECC 2011 ಗ್ರಾಮೀಣ ವಂಚಿತ ಮಾನದಂಡಗಳ ಪಟ್ಟಿಯಲ್ಲಿ ಸೇರ್ಪಡೆ',
        'ವಾರ್ಷಿಕ ಕುಟುಂಬ ಆದಾಯ ಅರ್ಹತಾ ಮಿತಿಯೊಳಗೆ ಇದೆ',
        'ಸಕ್ರಿಯ ಬಿಪಿಎಲ್ / ಅಂತ್ಯೋದಯ ರೇಷನ್ ಕಾರ್ಡ್'
      ],
      te: [
        'SECC 2011 గ్రామీణ జాబితా ప్రకారం అర్హత',
        'కుటుంబ వార్షిక ఆదాయం అర్హత పరిమితిలో ఉంది',
        'యాక్టివ్ రేషన్ కార్డు (BPL)'
      ]
    }
  },
  'pmay-g': {
    nativeName: {
      en: 'PMAY-G Rural Housing Scheme',
      hi: 'प्रधानमंत्री आवास योजना - ग्रामीण',
      kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಆವಾಸ್ ಯೋಜನೆ - ಗ್ರಾಮೀಣ',
      te: 'ప్రధానమంత్రి ఆవాస్ యోజన - గ్రామీణ్',
    },
    benefitHighlight: {
      en: '₹1.20 Lakh financial grant for pucca house construction + MGNREGA wages',
      hi: 'मैदानी क्षेत्रों में पक्का मकान निर्माण हेतु ₹1.20 लाख की सीधी सहायता',
      kn: 'ಗ್ರಾಮೀಣ ಪ್ರದೇಶದಲ್ಲಿ ಪಕ್ಕಾ ಮನೆ ನಿರ್ಮಾಣಕ್ಕೆ ₹1.20 ಲಕ್ಷ ನೇರ ಧನಸಹಾಯ + ನರೇಗಾ ಕೂಲಿ',
      te: 'గ్రామీణ ప్రాంతాల్లో పక్కా గృహ నిర్మాణానికి ₹1.20 లక్షల ఆర్థిక సహాయం + ఉపాధి హామీ వేతనం',
    },
    description: {
      en: 'Provides financial assistance to rural houseless and kutcha-house families to construct permanent homes.',
      hi: 'ग्रामीण क्षेत्रों में कच्चे या जर्जर मकानों में रहने वाले बेघर परिवारों को पक्के मकान हेतु आर्थिक सहायता।',
      kn: 'ಗ್ರಾಮೀಣ ಭಾಗದ ಮನೆರಹಿತ ಮತ್ತು ಕಚ್ಚಾ ಮನೆಯಲ್ಲಿ ವಾಸಿಸುವ ಕುಟುಂಬಗಳಿಗೆ ಮೂಲಸೌಕರ್ಯವುಳ್ಳ ಸುಸಜ್ಜಿತ ಪಕ್ಕಾ ಮನೆ ನಿರ್ಮಿಸಲು ಆರ್ಥಿಕ ನೆರವು.',
      te: 'గ్రామీణ ప్రాంతాల్లో ఇళ్లు లేని మరియు పూరిళ్లలో నివసించే నిరుపేద కుటుంబాలకు పక్కా ఇళ్ల నిర్మాణానికి ఆర్థిక సహాయం అందించే పథకం.',
    },
    matchingCriteria: {
      en: [
        'Rural resident without an existing pucca house',
        'OBC / BPL socio-economic status'
      ],
      hi: [
        'ग्रामीण निवासी जिसके पास पक्का मकान नहीं है',
        'ओबीसी / बीपीएल सामाजिक श्रेणी'
      ],
      kn: [
        'ಸ್ವಂತ ಪಕ್ಕಾ ಮನೆ ಹೊಂದಿರದ ಗ್ರಾಮೀಣ ನಿವಾಸಿ',
        'ಹಿಂದುಳಿದ ವರ್ಗ (OBC) / BPL ಕುಟುಂಬ'
      ],
      te: [
        'స్వంత పక్కా ఇల్లు లేని గ్రామీణ నివాసి',
        'వెనుకబడిన తరగతులు (OBC) / BPL వర్గం'
      ]
    },
    missingCriteria: {
      en: [
        'Verification of inclusion in Gram Panchayat Awaas+ list required',
        'Physical verification of kutcha dwelling by Village Officer'
      ],
      hi: [
        'ग्राम पंचायत Awaas+ 2018 सूची में नाम का सत्यापन आवश्यक',
        'ग्राम सचिव द्वारा कच्चे मकान की भौतिक पुष्टि'
      ],
      kn: [
        'ಗ್ರಾಮ ಪಂಚಾಯತ್ ಆವಾಸ್‌ಪ್ಲಸ್ (Awaas+) ಆದ್ಯತಾ ಪಟ್ಟಿಯಲ್ಲಿ ಹೆಸರು ಪರಿಶೀಲಿಸಬೇಕು',
        'ಗ್ರಾಮ ಪಂಚಾಯತಿ ಅಭಿವೃದ್ಧಿ ಅಧಿಕಾರಿಯಿಂದ (PDO) ಕಚ್ಚಾ ಮನೆ ದೃಢೀಕರಣ'
      ],
      te: [
        'గ్రామ పంచాయతీ Awaas+ ప్రాధాన్యత జాబితాలో పేరు ధృవీకరణ అవసరం',
        'గ్రామ కార్యదర్శి ద్వారా పూరింటి భౌతిక పరిశీలన'
      ]
    }
  },
  'pm-svanidhi': {
    nativeName: {
      en: 'PM SVANidhi Street Vendors Scheme',
      hi: 'पीएम स्वनिधि योजना',
      kn: 'ಪಿಎಂ ಸ್ವನಿಧಿ ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿಗಳ ಸಾಲ ಯೋಜನೆ',
      te: 'పీఎం స్వనిధి వీధి వ్యాపారుల రుణ పథకం',
    },
    benefitHighlight: {
      en: 'Collateral-free working capital loan up to ₹50,000 with 7% interest subsidy',
      hi: '₹10,000 से ₹50,000 तक बिना गारंटी का कार्यशील ऋण एवं 7% ब्याज सब्सिडी',
      kn: 'ಯಾವುದೇ ಭದ್ರತೆಯಿಲ್ಲದೆ ₹10,000 ರಿಂದ ₹50,000 ವರೆಗೆ ದುಡಿಯುವ ಬಂಡವಾಳ ಸಾಲ ಮತ್ತು 7% ಬಡ್ಡಿ ಸಬ್ಸಿಡಿ',
      te: 'హామీ లేకుండా ₹10,000 నుండి ₹50,000 వరకు పని మూలధన రుణం మరియు 7% వడ్డీ రాయితీ',
    },
    description: {
      en: 'Special micro-credit facility providing street vendors affordable working capital loans.',
      hi: 'स्ट्रीट वेंडर्स और रेहड़ी-पटरी वालों को अपना व्यवसाय बढ़ाने के लिए किफायती कार्यशील ऋण सुविधा।',
      kn: 'ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿಗಳು ತಮ್ಮ ವ್ಯಾಪಾರವನ್ನು ಪುನರಾರಂಭಿಸಲು ಮತ್ತು ಬೆಳೆಸಲು ಕಡಿಮೆ ಬಡ್ಡಿದರದಲ್ಲಿ ಕೈಗೆಟುಕುವ ಸಾಲ ಸೌಲಭ್ಯ.',
      te: 'వీధి వ్యాపారులు తమ జీవనోపాధిని పునరుద్ధరించుకోవడానికి సరసమైన వర్కింగ్ క్యాపిటల్ రుణ సదుపాయం.',
    },
    matchingCriteria: {
      en: [
        'Age between 18 and 60 years',
        'Self-employed informal street vendor'
      ],
      hi: [
        'आयु 18 से 60 वर्ष के मध्य',
        'स्वरोजगार अथवा स्ट्रीट वेंडर व्यवसाय'
      ],
      kn: [
        'ವಯಸ್ಸು 18 ರಿಂದ 60 ವರ್ಷಗಳ ಒಳಗೆ',
        'ಬೀದಿಬದಿ ವ್ಯಾಪಾರ ಅಥವಾ ಸ್ವಯಂ ಉದ್ಯೋಗ'
      ],
      te: [
        'వయస్సు 18 నుండి 60 సంవత్సరాల మధ్య',
        'వీధి వ్యాపారం లేదా స్వయం ఉపాధి'
      ]
    },
    missingCriteria: {
      en: ['Urban Local Body (ULB) Vending Certificate or Letter of Recommendation'],
      hi: ['नगर निकाय (ULB) द्वारा जारी वेंडिंग प्रमाण पत्र या अनुशंसा पत्र (LoR)'],
      kn: ['ನಗರ ಸ್ಥಳೀಯ ಸಂಸ್ಥೆ (ULB) ನೀಡಿದ ವ್ಯಾಪಾರ ಗುರುತಿನ ಚೀಟಿ ಅಥವಾ ಶಿಫಾರಸು ಪತ್ರ (LoR)'],
      te: ['పట్టణ స్థానిక సంస్థ (ULB) జారీ చేసిన వెండింగ్ సర్టిఫికేట్ లేదా సిఫార్సు లేఖ (LoR)']
    }
  },
  'pm-kmy': {
    nativeName: {
      en: 'PM Kisan Maan-Dhan Yojana',
      hi: 'प्रधानमंत्री किसान मान-धन योजना',
      kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಮಾನ್-ಧನ್ ಪಿಂಚಣಿ ಯೋಜನೆ',
      te: 'ప్రధానమంత్రి కిసాన్ మాన్-ధన్ పెన్షన్ పథకం',
    },
    benefitHighlight: {
      en: 'Assured ₹3,000/month lifelong social security pension after age 60',
      hi: '60 वर्ष की आयु पूर्ण होने पर ₹3,000 प्रति माह सुनिश्चित आजीवन पेंशन',
      kn: '೬೦ ವರ್ಷ ವಯಸ್ಸಿನ ನಂತರ ಮಾಸಿಕ ₹3,000 ಖಾತರಿಯ ಆಜೀವ ಪಿಂಚಣಿ',
      te: '60 సంవత్సరాల వయస్సు దాటిన తర్వాత నెలకు ₹3,000 హామీతో కూడిన జీవితకాల పెన్షన్',
    },
    description: {
      en: 'Old-age pension scheme for small and marginal farmers guaranteeing ₹3,000 monthly pension.',
      hi: 'छोटे और सीमांत किसानों के वृद्धावस्था सामाजिक सुरक्षा हेतु केंद्र सरकार का 50% सह-अंशदान पेंशन कार्यक्रम।',
      kn: 'ಸಣ್ಣ ಮತ್ತು ಅತಿ ಸಣ್ಣ ರೈತರ ವೃದ್ಧಾಪ್ಯ ಭದ್ರತೆಗಾಗಿ ಸರ್ಕಾರದ 50% ಸಮಾನ ವಂತಿಗೆಯೊಂದಿಗೆ ಖಾತರಿಯ ಪಿಂಚಣಿ ಯೋಜನೆ.',
      te: 'చిన్న మరియు సన్నకారు రైతుల వృద్ధాప్య రక్షణ కోసం ప్రభుత్వ సమాన వాటాతో నెలవారీ పెన్షన్ పథకం.',
    },
    matchingCriteria: {
      en: [
        'Age is 38 years (within 18-40 age window)',
        'Cultivable landholding is below 2.0 hectares',
        'Small and marginal farmer category'
      ],
      hi: [
        'आयु 38 वर्ष (प्रवेश आयु 18-40 वर्ष के अंतर्गत)',
        '2 हेक्टेयर से कम कृषि भूमि',
        'लघु अथवा सीमांत किसान श्रेणी'
      ],
      kn: [
        'ಪ್ರಸ್ತುತ ವಯಸ್ಸು 38 ವರ್ಷ (18-40 ವಯೋಮಿತಿಯೊಳಗೆ)',
        '2.0 ಹೆಕ್ಟೇರ್‌ಗಿಂತ ಕಡಿಮೆ ಕೃಷಿ ಭೂಮಿ',
        'ಸಣ್ಣ ಅಥವಾ ಅತಿ ಸಣ್ಣ ರೈತ'
      ],
      te: [
        'వయస్సు 38 సంవత్సరాలు (18-40 సంవత్సరాల అర్హత పరిధి)',
        '2.0 హెక్టార్ల కంటే తక్కువ వ్యవసాయ భూమి',
        'చిన్న లేదా సన్నకారు రైతు వర్గం'
      ]
    }
  },
  'pmmvy': {
    nativeName: {
      en: 'Pradhan Mantri Matru Vandana Yojana',
      hi: 'प्रधानमंत्री मातृ वंदना योजना',
      kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಮಾತೃ ವಂದನಾ ಯೋಜನೆ',
      te: 'ప్రధానమంత్రి మాతృ వందన యోజన',
    },
    benefitHighlight: {
      en: '₹5,000 - ₹6,000 conditional cash incentive for pregnant and lactating mothers',
      hi: 'गर्भवती और धात्री माताओं के लिए ₹5,000 - ₹6,000 की मातृत्व नकद सहायता',
      kn: 'ಗರ್ಭಿಣಿಯರು ಮತ್ತು ಬಾಣಂತಿಯರಿಗೆ ₹5,000 ರಿಂದ ₹6,000 ರವರೆಗೆ ಮಾತೃತ್ವ ಆರ್ಥಿಕ ಪ್ರೋತ್ಸಾಹಧನ',
      te: 'గర్భిణీ స్త్రీలు మరియు బాలింతలకు ₹5,000 నుండి ₹6,000 వరకు ఆర్థిక సహాయం',
    },
    description: {
      en: 'Maternity benefit program providing cash incentives for pregnant and lactating mothers.',
      hi: 'गर्भवती महिलाओं और स्तनपान कराने वाली माताओं के स्वास्थ्य एवं पोषण में सुधार हेतु केंद्र प्रायोजित प्रत्यक्ष लाभ योजना।',
      kn: 'ಗರ್ಭಿಣಿಯರ ಮತ್ತು ನವಜಾತ ಶಿಶುಗಳ ಪೌಷ್ಟಿಕತೆ ಹಾಗೂ ಆರೋಗ್ಯ ಸುಧಾರಣೆಗಾಗಿ ಸರ್ಕಾರದ ನೇರ ನಗದು ನೆರವು ಯೋಜನೆ.',
      te: 'గర్భిణులు మరియు బాలింతల పోషకాహార మరియు ఆరోగ్య మెరుగుదల కోసం ప్రత్యక్ష నగదు బదిలీ పథకం.',
    },
    matchingCriteria: {
      en: [],
      hi: [],
      kn: [],
      te: []
    },
    failedCriteria: {
      en: [
        'Gender requirement: Beneficiary must be a pregnant or lactating mother (Current profile: Male)',
        'Mandatory maternity registration at Anganwadi / Health Centre'
      ],
      hi: [
        'लिंग मापदंड: केवल गर्भवती महिला अथवा धात्री माताएं पात्र हैं (वर्तमान प्रोफ़ाइल: पुरुष)',
        'आंगनवाड़ी या अधिकृत स्वास्थ्य केंद्र में मातृ पंजीकरण अनिवार्य'
      ],
      kn: [
        'ಲಿಂಗ ಮಾನದಂಡ: ಕೇವಲ ಗರ್ಭಿಣಿಯರು ಅಥವಾ ಹಾಲುಣಿಸುವ ತಾಯಂದಿರು ಮಾತ್ರ ಅರ್ಹರು (ಪ್ರಸ್ತುತ ಪ್ರೊಫೈಲ್: ಪುರುಷ)',
        'ಅಂಗನವಾಡಿ ಅಥವಾ ಆರೋಗ್ಯ ಕೇಂದ್ರದಲ್ಲಿ ಮಾತೃತ್ವ ನೋಂದಣಿ ಕಡ್ಡಾಯ'
      ],
      te: [
        'లింగ ప్రమాణం: గర్భిణీ లేదా బాలింతలు మాత్రమే అర్హులు (ప్రస్తుత ప్రొఫైల్: పురుషుడు)',
        'అంగన్‌వాడీ లేదా ఆరోగ్య కేంద్రంలో గర్భధారణ నమోదు తప్పనిసరి'
      ]
    }
  },
  'pm-kusum': {
    nativeName: {
      en: 'PM-KUSUM Solar Agriculture Pump Scheme',
      hi: 'पीएम-कुसुम सौर कृषि पंप योजना',
      kn: 'ಪಿಎಂ-ಕುಸುಮ್ ಸೌರ ಕೃಷಿ ಪಂಪ್‌ಸೆಟ್ ಯೋಜನೆ',
      te: 'పీఎం-కుసుమ్ సౌర వ్యవసాయ పంపు పథకం',
    },
    benefitHighlight: {
      en: 'Up to 60% capital subsidy on standalone solar agriculture pumps',
      hi: 'सोलर पंप लगाने पर केंद्र व राज्य सरकार द्वारा 60% तक भारी पूंजीगत सब्सिडी',
      kn: 'ಸೌರ ಕೃಷಿ ನೀರಾವರಿ ಪಂಪ್ ಅಳವಡಿಕೆಗೆ ಕೇಂದ್ರ ಹಾಗೂ ರಾಜ್ಯ ಸರ್ಕಾರಗಳಿಂದ 60% ರವರೆಗೆ ಸಬ್ಸಿಡಿ',
      te: 'సోలార్ వ్యవసాయ నీటి పంపు ఏర్పాటుకు ప్రభుత్వం నుండి 60% వరకు సబ్సిడీ',
    },
    description: {
      en: 'Enables farmers to set up standalone solar pumps for reliable agricultural irrigation.',
      hi: 'सिंचाई के लिए ग्रिड पर निर्भरता घटाने और सौर ऊर्जा से पानी पंप करने हेतु किसानों को भारी सब्सिडी।',
      kn: 'ರೈತರು ಕೃಷಿ ನೀರಾವರಿಗಾಗಿ ಸೋಲಾರ್ ಪಂಪ್‌ಸೆಟ್‌ಗಳನ್ನು ಅಳವಡಿಸಿಕೊಳ್ಳಲು ಸರ್ಕಾರದ ಭಾರಿ ಸಬ್ಸಿಡಿ ಯೋಜನೆ.',
      te: 'రైతులు సాగునీటి కోసం సోలಾರ್ పంపులను ఏర్పాటు చేసుకోవడానికి ప్రభుత్వం భారీ సబ్సిడీ అందిస్తుంది.',
    },
    matchingCriteria: {
      en: [
        'Possesses agricultural land requiring irrigation',
        'Located in designated rural agricultural feeder zone'
      ],
      hi: [
        'सिंचाई योग्य कृषि भूमि धारक',
        'ग्रामीण कृषि फीडर क्षेत्र में स्थित'
      ],
      kn: [
        'ನೀರಾವರಿ ಅಗತ್ಯವಿರುವ ಕೃಷಿ ಭೂಮಿ ಹೊಂದಿರುವುದು',
        'ಗ್ರಾಮೀಣ ಕೃಷಿ ವಿದ್ಯುತ್ ಫೀಡರ್ ವ್ಯಾಪ್ತಿಯಲ್ಲಿ ಇರುವುದು'
      ],
      te: [
        'సాగునీటి అవసరం ఉన్న వ్యవసాయ భూమిని కలిగి ఉండటం',
        'గ్రామీణ వ్యవసాయ విద్యుత్ ఫీడర్ పరిధిలో ఉండటం'
      ]
    }
  }
};

/**
 * Returns a scheme object localized for the target language (en, hi, kn, te)
 */
export const getLocalizedScheme = (scheme: Scheme, lang: Language): Scheme => {
  // If the scheme was mapped from live backend via mapBackendSchemeToFrontend,
  // it is already authoritatively localized and its bilingual subtitle properly computed.
  if (scheme.verifiedOfficial) {
    return scheme;
  }

  const content = SCHEME_TRANSLATIONS[scheme.id];
  if (!content) return scheme;

  const validLang: Language = (lang in content.nativeName) ? lang : 'en';

  return {
    ...scheme,
    nativeName: content.nativeName[validLang] || scheme.nativeName,
    benefitHighlight: content.benefitHighlight[validLang] || scheme.benefitHighlight,
    description: content.description[validLang] || scheme.description,
    matchingCriteria: content.matchingCriteria[validLang] || scheme.matchingCriteria,
    missingCriteria: content.missingCriteria ? (content.missingCriteria[validLang] || scheme.missingCriteria) : scheme.missingCriteria,
    failedCriteria: content.failedCriteria ? (content.failedCriteria[validLang] || scheme.failedCriteria) : scheme.failedCriteria,
  };
};

export const CATEGORY_LABELS: Record<string, Record<Language, string>> = {
  all: {
    en: 'All Schemes',
    hi: 'सभी योजनाएं',
    kn: 'ಎಲ್ಲಾ ಯೋಜನೆಗಳು',
    te: 'అన్ని పథకాలు',
  },
  agriculture: {
    en: 'Agriculture & Farming',
    hi: 'कृषि कल्याण',
    kn: 'ಕೃಷಿ ಕಲ್ಯಾಣ',
    te: 'వ్యవసాయం & రైతు',
  },
  healthcare: {
    en: 'Healthcare & Medical',
    hi: 'स्वास्थ्य सुरक्षा',
    kn: 'ಆರೋಗ್ಯ ರಕ್ಷಣೆ',
    te: 'వైద్య సంరక్షణ',
  },
  housing: {
    en: 'Housing & Shelter',
    hi: 'ग्रामीण आवास',
    kn: 'ಗ್ರಾಮೀಣ ವಸತಿ',
    te: 'గ్రామీణ గృహనిర్మాణం',
  },
  social_welfare: {
    en: 'Social Welfare & Pension',
    hi: 'सामाजिक सुरक्षा',
    kn: 'ಸಾಮಾಜಿಕ ಭದ್ರತೆ',
    te: 'సామాజిక భద్రత',
  },
  employment: {
    en: 'Employment & Skills',
    hi: 'रोजगार व उद्यम',
    kn: 'ಉದ್ಯೋಗ ಮತ್ತು ಕೌಶಲ್ಯ',
    te: 'ఉపాధి & నైపుణ్యాలు',
  },
  education: {
    en: 'Education & Youth',
    hi: 'शिक्षा व छात्रवृत्ति',
    kn: 'ಶಿಕ್ಷಣ ಮತ್ತು ವಿದ್ಯಾರ್ಥಿವೇತನ',
    te: 'విద్య & స్కాలర్‌షిప్‌లు',
  },
  women_and_child: {
    en: 'Women & Child Welfare',
    hi: 'महिला एवं बाल विकास',
    kn: 'ಮಹಿಳಾ ಮತ್ತು ಮಕ್ಕಳ ಕಲ್ಯಾಣ',
    te: 'మహిళా మరియు శిశు సంక్షేమం',
  },
  energy: {
    en: 'Clean Energy & Solar',
    hi: 'स्वच्छ ऊर्जा व सोलर',
    kn: 'ಸ್ವಚ್ಛ ಇಂಧನ & ಸೌರ',
    te: 'స్వచ్ఛమైన శక్తి & సోలార్',
  },
};
