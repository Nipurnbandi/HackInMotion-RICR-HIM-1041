import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
];

const STORAGE_KEY = "smartcity-language";

// English lives inline in the components as t()'s fallback text, so a
// missing key can never break the UI. Hindi is the first regional pack;
// adding another language is just another dictionary here.
const HINDI = {
  // Shell / navigation
  "nav.home": "होम",
  "nav.citymap": "शहर का नक्शा",
  "nav.report": "रिपोर्ट करें",
  "nav.myreports": "मेरी रिपोर्टें",
  "nav.help": "सहायता",
  "nav.profile": "प्रोफ़ाइल",
  "nav.logout": "लॉग आउट",
  "brand.sub": "नागरिक पोर्टल",
  "footer.note":
    "SmartCity नागरिक समस्या रिपोर्टिंग · रिपोर्टों की समीक्षा आपका नगर प्रशासन करता है।",
  "footer.transparency": "शहर का पारदर्शिता रिपोर्ट कार्ड",
  "common.loading": "लोड हो रहा है…",
  "common.tryagain": "फिर से कोशिश करें",
  "common.reportIssue": "+ समस्या रिपोर्ट करें",

  // Statuses
  "status.SUBMITTED.label": "दर्ज हुई",
  "status.SUBMITTED.desc": "हमें आपकी रिपोर्ट मिल गई है।",
  "status.UNDER_REVIEW.label": "समीक्षा में",
  "status.UNDER_REVIEW.desc": "एक नगर अधिकारी विवरण की जाँच कर रहे हैं।",
  "status.IN_PROGRESS.label": "कार्य जारी",
  "status.IN_PROGRESS.desc": "इस समस्या पर काम शुरू हो चुका है।",
  "status.RESOLVED.label": "हल हो गई",
  "status.RESOLVED.desc": "समस्या ठीक कर दी गई है।",
  "status.REJECTED.label": "अस्वीकृत",
  "status.REJECTED.desc": "यह रिपोर्ट आगे नहीं बढ़ाई जा सकी।",

  // Categories
  "category.STREETLIGHT.label": "स्ट्रीटलाइट",
  "category.STREETLIGHT.hint": "बत्ती बंद, टिमटिमाती या खंभा क्षतिग्रस्त",
  "category.POTHOLE.label": "सड़क का गड्ढा",
  "category.POTHOLE.hint": "सड़क की सतह टूटी या क्षतिग्रस्त",
  "category.GARBAGE_OVERFLOW.label": "कचरा अतिप्रवाह",
  "category.GARBAGE_OVERFLOW.hint": "कूड़ेदान भरा है या कचरा नहीं उठाया गया",
  "category.WATER_LEAKAGE.label": "पानी का रिसाव",
  "category.WATER_LEAKAGE.hint": "पाइप फटा, मुख्य लाइन से रिसाव या पानी की बर्बादी",
  "category.DAMAGED_PUBLIC_PROPERTY.label": "सार्वजनिक संपत्ति क्षति",
  "category.DAMAGED_PUBLIC_PROPERTY.hint": "टूटी बेंच, रेलिंग, साइनबोर्ड या शेल्टर",
  "category.ILLEGAL_DUMPING.label": "अवैध कचरा डंपिंग",
  "category.ILLEGAL_DUMPING.hint": "अनधिकृत जगह पर कचरा फेंका गया",
  "category.BROKEN_DRAINAGE.label": "टूटी जल निकासी",
  "category.BROKEN_DRAINAGE.hint": "बंद नाली, खुला मैनहोल या जलभराव",

  // Citizen dashboard
  "dashboard.greeting.morning": "सुप्रभात",
  "dashboard.greeting.afternoon": "नमस्ते",
  "dashboard.greeting.evening": "शुभ संध्या",
  "dashboard.subtitle":
    "नागरिक समस्या रिपोर्ट करें और अपने शहर को बेहतर बनाएं। हर रिपोर्ट को एक ट्रैकिंग आईडी मिलती है ताकि आप समाधान तक उस पर नज़र रख सकें।",
  "dashboard.myreports": "मेरी रिपोर्टें",
  "dashboard.stats.total": "कुल रिपोर्टें",
  "dashboard.stats.submitted": "दर्ज हुईं",
  "dashboard.stats.inprogress": "कार्य जारी",
  "dashboard.stats.resolved": "हल हुईं",
  "dashboard.recent": "हाल की रिपोर्टें",
  "dashboard.viewall": "सभी रिपोर्टें देखें",
  "dashboard.loading": "आपका डैशबोर्ड लोड हो रहा है…",
  "dashboard.empty.title": "आपने अभी तक कुछ रिपोर्ट नहीं किया है",
  "dashboard.empty.message":
    "कोई गड्ढा, खराब स्ट्रीटलाइट या भरा कूड़ेदान दिखा? रिपोर्ट करें, नगर प्रशासन उसे देखेगा।",
  "dashboard.empty.cta": "अपनी पहली समस्या रिपोर्ट करें",
  "dashboard.tips.title": "जानने योग्य बातें",

  // My reports
  "myreports.title": "मेरी रिपोर्टें",
  "myreports.subtitle": "आपने जो भी रिपोर्ट किया है, और वह कहाँ तक पहुँचा।",
  "myreports.search": "विवरण, पता या ट्रैकिंग आईडी से खोजें…",
  "myreports.all": "सभी",
  "myreports.loading": "आपकी रिपोर्टें लोड हो रही हैं…",
  "myreports.reports": "रिपोर्टें",
  "myreports.report": "रिपोर्ट",
  "myreports.prev": "पिछला",
  "myreports.next": "अगला",
  "myreports.page": "पृष्ठ",
  "myreports.of": "में से",

  // Report wizard
  "report.title": "समस्या रिपोर्ट करें",
  "report.subtitle":
    "पाँच छोटे चरण। आपकी रिपोर्ट ट्रैकिंग आईडी के साथ सीधे नगर प्रशासन तक जाती है।",
  "report.step": "चरण",
  "report.stepOf": "में से",
  "report.steps.category": "समस्या क्या है?",
  "report.steps.location": "समस्या कहाँ है?",
  "report.steps.photo": "फोटो प्रमाण जोड़ें",
  "report.steps.description": "समस्या का विवरण दें",
  "report.steps.review": "जाँचें और भेजें",
  "report.describeLabel": "समस्या का विवरण दें",
  "report.describeHint":
    "क्या खराब है, कब से ऐसा है, और क्या किसी को खतरा है?",
  "report.minChars": "कम से कम {n} अक्षर",
  "report.back": "पीछे",
  "report.cancel": "रद्द करें",
  "report.continue": "आगे बढ़ें",
  "report.submit": "रिपोर्ट भेजें",
  "report.submitting": "भेजा जा रहा है…",
  "report.review.category": "श्रेणी",
  "report.review.location": "स्थान",
  "report.review.photo": "फोटो प्रमाण",
  "report.review.description": "विवरण",
  "report.review.nophoto": "कोई फोटो संलग्न नहीं",
  "report.review.note":
    "आपकी रिपोर्ट आपके खाते में दर्ज होगी और उसे एक ट्रैकिंग आईडी मिलेगी। काम शुरू होने से पहले नगर कर्मचारी हर रिपोर्ट की समीक्षा करते हैं।",
  "report.success.title": "समस्या सफलतापूर्वक रिपोर्ट हुई",
  "report.success.message":
    "अपने शहर को बेहतर बनाने में मदद के लिए धन्यवाद। आपकी रिपोर्ट नगर प्रशासन को भेज दी गई है।",
  "report.success.tracking": "ट्रैकिंग आईडी",
  "report.success.status": "स्थिति",
  "report.success.hint":
    "यह ट्रैकिंग आईडी संभालकर रखें। आप 'मेरी रिपोर्टें' से कभी भी इस रिपोर्ट की प्रगति देख सकते हैं।",
  "report.success.viewall": "मेरी रिपोर्टें देखें",
  "report.success.viewthis": "यह रिपोर्ट देखें",

  // Issue details
  "details.back": "← मेरी रिपोर्टों पर वापस",
  "details.issue": "समस्या",
  "details.progress": "प्रगति",
  "details.reportdetails": "रिपोर्ट विवरण",
  "details.category": "श्रेणी",
  "details.reported": "रिपोर्ट की गई",
  "details.updated": "अंतिम अपडेट",
  "details.description": "विवरण",
  "details.location": "स्थान",
  "details.address": "पता",
  "details.coordinates": "निर्देशांक",
  "details.photo": "फोटो प्रमाण",
  "details.nophoto": "इस रिपोर्ट के साथ कोई फोटो संलग्न नहीं थी।",
  "details.resolution": "समाधान",
  "details.history": "गतिविधि इतिहास",
  "details.submittedEntry": "रिपोर्ट दर्ज हुई",
  "details.proofAdded": "समाधान का प्रमाण जोड़ा गया",
  "details.byReporter": "रिपोर्टकर्ता",
  "details.byAdmin": "नगर प्रशासन",
  "details.confirmQuestion": "हल के रूप में चिह्नित — क्या यह आपको ठीक लगता है?",
  "details.confirmYes": "हाँ, ठीक हो गया",
  "details.confirming": "पुष्टि हो रही है…",
  "details.reopenNo": "नहीं, फिर से खोलें",
  "details.reopening": "फिर से खोला जा रहा है…",
  "details.confirmedThanks":
    "✅ आपने इस समाधान की पुष्टि की। धन्यवाद!",
  "details.loading": "रिपोर्ट लोड हो रही है…",

  // City map
  "map.title": "शहर का नक्शा",
  "map.subtitle":
    "शहर भर में रिपोर्ट की गई हर समस्या का लाइव नक्शा — दोबारा रिपोर्ट करने से पहले देखें कि आपके पड़ोसियों ने क्या पहले ही बताया है।",
  "map.issuesOnMap": "नक्शे पर समस्याएँ",
  "map.issueOnMap": "नक्शे पर समस्या",
  "map.colorby": "रंग आधार",
  "map.status": "स्थिति",
  "map.category": "श्रेणी",
  "map.reports": "रिपोर्टें",
  "map.report": "रिपोर्ट",
  "map.support": "समर्थन करें",
  "map.supported": "समर्थित",
  "map.loading": "शहर का नक्शा लोड हो रहा है…",
  "map.escalated": "उच्च अधिकारी को भेजा गया",
  "map.supporters": "नागरिकों ने समर्थन किया",
  "map.empty.title": "नक्शे पर अभी कुछ नहीं है",
  "map.voteError": "हम आपका वोट दर्ज नहीं कर सके।",
};

const TRANSLATIONS = { hi: HINDI };

function defaultT(key, fallback) {
  return fallback ?? key;
}

const LanguageContext = createContext({
  lang: "en",
  setLang: () => {},
  t: defaultT,
});

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === "en" || TRANSLATIONS[stored] ? stored : "en";
    } catch {
      return "en";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // Private mode — the choice simply won't persist.
    }
    document.documentElement.lang = lang;
  }, [lang]);

  const t = useCallback(
    (key, fallback) => TRANSLATIONS[lang]?.[key] ?? fallback ?? key,
    [lang]
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, t]);
  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export function useI18n() {
  return useContext(LanguageContext);
}
