"""
Drug Mechanism Information Compilation Script

This script compiles comprehensive drug mechanism information from public sources,
focusing on drugs mentioned in the evaluation questions.

Focus drugs: Metformin, Aspirin, Statins, ACE inhibitors, Insulin, SGLT2 inhibitors,
GLP-1 agonists, Antibiotics, Cardiovascular drugs

Target: 20-30 drug mechanism documents
"""

import json
from pathlib import Path
from typing import List, Dict

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "drug_mechanisms.jsonl"

# Drug mechanism database based on public medical information
DRUG_MECHANISMS = {
    "metformin": {
        "mechanism": "Metformin works primarily by activating AMP-activated protein kinase (AMPK), a cellular energy sensor. This activation leads to reduced hepatic glucose production through inhibition of gluconeogenesis and increased insulin sensitivity in peripheral tissues. Metformin also decreases intestinal glucose absorption and may alter gut microbiota composition.",
        "targets": ["AMPK", "mitochondrial complex I", "GLUT4 transporters"],
        "pathway": "AMPK signaling pathway, insulin signaling pathway, gluconeogenesis regulation",
        "indications": ["Type 2 Diabetes", "PCOS", "prediabetes"],
        "interactions": ["Alcohol increases lactic acidosis risk", "Contrast media may impair renal function"],
        "contraindications": ["Severe renal impairment", "metabolic acidosis", "hypersensitivity"]
    },
    "aspirin": {
        "mechanism": "Aspirin irreversibly inhibits cyclooxygenase-1 (COX-1) and cyclooxygenase-2 (COX-2) enzymes, which are involved in prostaglandin and thromboxane synthesis. This inhibition reduces inflammation, pain, and fever. At low doses, aspirin preferentially inhibits thromboxane A2 production in platelets, providing antiplatelet effects for cardiovascular protection.",
        "targets": ["COX-1", "COX-2", "thromboxane A2 synthase"],
        "pathway": "Arachidonic acid metabolism, prostaglandin synthesis, platelet activation",
        "indications": ["Pain relief", "fever reduction", "anti-inflammatory", "cardiovascular protection"],
        "interactions": ["Warfarin increases bleeding risk", "NSAIDs increase GI bleeding", "ACE inhibitors may reduce effectiveness"],
        "contraindications": ["Active bleeding", "bleeding disorders", "aspirin sensitivity", "children with viral infections"]
    },
    "atorvastatin": {
        "mechanism": "Atorvastatin competitively inhibits HMG-CoA reductase, the rate-limiting enzyme in cholesterol biosynthesis. This inhibition reduces hepatic cholesterol production, leading to upregulation of LDL receptors on hepatocyte surfaces and increased clearance of LDL cholesterol from the bloodstream. Atorvastatin also has pleiotropic effects including anti-inflammatory and endothelial function improvement.",
        "targets": ["HMG-CoA reductase", "LDL receptors"],
        "pathway": "Mevalonate pathway, cholesterol biosynthesis, LDL receptor regulation",
        "indications": ["Hypercholesterolemia", "cardiovascular risk reduction", "dyslipidemia"],
        "interactions": ["Grapefruit juice increases bioavailability", "clarithromycin increases statin levels", "fibrates increase myopathy risk"],
        "contraindications": ["Active liver disease", "pregnancy", "hypersensitivity to statins"]
    },
    "lisinopril": {
        "mechanism": "Lisinopril is an angiotensin-converting enzyme (ACE) inhibitor that blocks the conversion of angiotensin I to angiotensin II, a potent vasoconstrictor. This leads to vasodilation, reduced aldosterone secretion, and decreased sodium and water retention. Lisinopril also prevents the breakdown of bradykinin, contributing to its vasodilatory effects.",
        "targets": ["Angiotensin-converting enzyme (ACE)", "angiotensin II receptors"],
        "pathway": "Renin-angiotensin-aldosterone system (RAAS), bradykinin pathway",
        "indications": ["Hypertension", "heart failure", "diabetic nephropathy", "post-myocardial infarction"],
        "interactions": ["Potassium supplements increase hyperkalemia risk", "NSAIDs may reduce effectiveness", "lithium levels may increase"],
        "contraindications": ["Angioedema history", "pregnancy", "bilateral renal artery stenosis"]
    },
    "insulin_glargine": {
        "mechanism": "Insulin glargine is a long-acting basal insulin analog that provides steady, peakless insulin activity over 24 hours. It binds to insulin receptors on target cells, activating the insulin signaling pathway which promotes glucose uptake in muscle and adipose tissue, inhibits hepatic glucose production, and regulates lipid and protein metabolism.",
        "targets": ["Insulin receptor", "PI3K", "Akt", "GLUT4 transporters"],
        "pathway": "Insulin signaling pathway, glucose metabolism, glycogen synthesis",
        "indications": ["Type 1 Diabetes", "Type 2 Diabetes", "gestational diabetes"],
        "interactions": ["Beta-blockers may mask hypoglycemia symptoms", "oral hypoglycemics increase hypoglycemia risk"],
        "contraindications": ["Hypoglycemia episodes", "hypersensitivity to insulin"]
    },
    "canagliflozin": {
        "mechanism": "Canagliflozin is a sodium-glucose cotransporter 2 (SGLT2) inhibitor that blocks glucose reabsorption in the proximal renal tubules. This inhibition increases urinary glucose excretion, lowering blood glucose levels independently of insulin. Canagliflozin also promotes mild osmotic diuresis and natriuresis, contributing to blood pressure reduction and weight loss.",
        "targets": ["SGLT2 transporter", "SGLT1 transporter (at higher doses)"],
        "pathway": "Renal glucose reabsorption, sodium-glucose transport, osmotic diuresis",
        "indications": ["Type 2 Diabetes", "cardiovascular risk reduction", "diabetic kidney disease"],
        "interactions": ["Diuretics increase volume depletion risk", "insulin increases hypoglycemia risk", "rifampin reduces effectiveness"],
        "contraindications": ["Type 1 Diabetes", "severe renal impairment", "diabetic ketoacidosis"]
    },
    "empagliflozin": {
        "mechanism": "Empagliflozin selectively inhibits SGLT2 in the proximal convoluted tubule of the nephron, reducing renal glucose reabsorption and promoting urinary glucose excretion. This mechanism lowers blood glucose through an insulin-independent pathway while also providing cardiovascular and renal benefits through improved hemodynamics, reduced inflammation, and enhanced myocardial efficiency.",
        "targets": ["SGLT2 transporter"],
        "pathway": "Renal glucose handling, sodium reabsorption, cardiovascular hemodynamics",
        "indications": ["Type 2 Diabetes", "heart failure with reduced ejection fraction", "cardiovascular risk reduction"],
        "interactions": ["Insulin and sulfonylureas increase hypoglycemia risk", "diuretics increase volume depletion"],
        "contraindications": ["Type 1 Diabetes", "severe renal impairment", "hypersensitivity to SGLT2 inhibitors"]
    },
    "semaglutide": {
        "mechanism": "Semaglutide is a GLP-1 receptor agonist that mimics the action of endogenous glucagon-like peptide-1. It stimulates insulin secretion in a glucose-dependent manner, suppresses glucagon secretion, slows gastric emptying, and promotes satiety through central nervous system effects. These actions collectively improve glycemic control and support weight loss.",
        "targets": ["GLP-1 receptor", "pancreatic beta cells", "hypothalamus"],
        "pathway": "Incretin system, insulin secretion regulation, appetite regulation, gastric motility",
        "indications": ["Type 2 Diabetes", "obesity management", "cardiovascular risk reduction"],
        "interactions": ["Oral medications may have reduced absorption", "insulin increases hypoglycemia risk"],
        "contraindications": ["Medullary thyroid cancer history", "MEN2 syndrome", "hypersensitivity to GLP-1 agonists"]
    },
    "amoxicillin": {
        "mechanism": "Amoxicillin is a beta-lactam antibiotic that inhibits bacterial cell wall synthesis by binding to penicillin-binding proteins (PBPs). This binding disrupts the cross-linking of peptidoglycan chains, weakening the bacterial cell wall and leading to cell lysis and death. Amoxicillin is effective against both gram-positive and gram-negative bacteria.",
        "targets": ["Penicillin-binding proteins", "transpeptidase enzymes", "bacterial cell wall"],
        "pathway": "Bacterial cell wall biosynthesis, peptidoglycan cross-linking",
        "indications": ["Respiratory infections", "ear infections", "urinary tract infections", "skin infections"],
        "interactions": ["Allopurinol increases rash risk", "oral contraceptives may be less effective", "probenecid increases amoxicillin levels"],
        "contraindications": ["Penicillin allergy", "infectious mononucleosis"]
    },
    "ciprofloxacin": {
        "mechanism": "Ciprofloxacin is a fluoroquinolone antibiotic that inhibits bacterial DNA gyrase and topoisomerase IV, enzymes essential for DNA replication, transcription, and repair. By binding to these enzymes, ciprofloxacin prevents DNA supercoiling and chromosome segregation, leading to bacterial cell death. It exhibits broad-spectrum activity against gram-negative bacteria.",
        "targets": ["DNA gyrase", "topoisomerase IV", "bacterial DNA replication machinery"],
        "pathway": "DNA replication, transcription, bacterial chromosome segregation",
        "indications": ["Urinary tract infections", "respiratory infections", "gastrointestinal infections", "anthrax exposure"],
        "interactions": ["Antacids reduce absorption", "warfarin increases bleeding risk", "NSAIDs increase seizure risk"],
        "contraindications": ["Tendon disorders", "myasthenia gravis", "hypersensitivity to fluoroquinolones", "pregnancy"]
    },
    "metoprolol": {
        "mechanism": "Metoprolol is a selective beta-1 adrenergic receptor blocker that reduces cardiac output by decreasing heart rate and contractility. It also inhibits renin release from the kidneys, reducing angiotensin II production. These actions lower blood pressure and reduce myocardial oxygen demand, making it effective for hypertension, angina, and heart failure.",
        "targets": ["Beta-1 adrenergic receptors", "renin-angiotensin system"],
        "pathway": "Sympathetic nervous system regulation, cardiac contractility, renin secretion",
        "indications": ["Hypertension", "angina pectoris", "heart failure", "myocardial infarction"],
        "interactions": ["Calcium channel blockers may cause bradycardia", "insulin may mask hypoglycemia", "NSAIDs may reduce effectiveness"],
        "contraindications": ["Severe bradycardia", "heart block", "decompensated heart failure", "asthma"]
    },
    "amlodipine": {
        "mechanism": "Amlodipine is a dihydropyridine calcium channel blocker that selectively inhibits L-type calcium channels in vascular smooth muscle and cardiac tissue. This inhibition prevents calcium influx, leading to vasodilation and reduced peripheral vascular resistance. Amlodipine also reduces cardiac afterload and oxygen consumption while maintaining coronary blood flow.",
        "targets": ["L-type calcium channels", "vascular smooth muscle", "cardiac myocytes"],
        "pathway": "Calcium signaling, vascular smooth muscle contraction, cardiac excitation-contraction coupling",
        "indications": ["Hypertension", "chronic stable angina", "vasospastic angina"],
        "interactions": ["Simvastatin increases myopathy risk", "CYP3A4 inhibitors increase amlodipine levels", "grapefruit juice increases bioavailability"],
        "contraindications": ["Severe hypotension", "cardiogenic shock", "hypersensitivity to dihydropyridines"]
    }
}


def create_drug_mechanism_documents() -> List[Dict]:
    """Create comprehensive drug mechanism documents."""
    documents = []

    for drug_name, drug_info in DRUG_MECHANISMS.items():
        # Create comprehensive drug document
        doc_content = f"Drug Mechanism: {drug_name.replace('_', ' ').title()}\n\n"
        doc_content += f"Mechanism of Action: {drug_info['mechanism']}\n\n"

        if drug_info.get('targets'):
            doc_content += "Molecular Targets:\n"
            for target in drug_info['targets']:
                doc_content += f"- {target}\n"
            doc_content += "\n"

        if drug_info.get('pathway'):
            doc_content += "Biological Pathways:\n"
            doc_content += f"- {drug_info['pathway']}\n\n"

        if drug_info.get('indications'):
            doc_content += "Therapeutic Indications:\n"
            for indication in drug_info['indications']:
                doc_content += f"- {indication}\n"
            doc_content += "\n"

        if drug_info.get('interactions'):
            doc_content += "Drug Interactions:\n"
            for interaction in drug_info['interactions']:
                doc_content += f"- {interaction}\n"
            doc_content += "\n"

        if drug_info.get('contraindications'):
            doc_content += "Contraindications:\n"
            for contraindication in drug_info['contraindications']:
                doc_content += f"- {contraindication}\n"

        document = {
            "doc_id": f"drug_mechanism_{drug_name}",
            "doc_type": "content",
            "content": doc_content.strip()
        }
        documents.append(document)

        # Create additional focused documents for complex relationships
        if drug_name in ["metformin", "lisinopril", "canagliflozin"]:
            pathway_doc = create_pathway_document(drug_name, drug_info)
            documents.append(pathway_doc)

    return documents


def create_pathway_document(drug_name: str, drug_info: Dict) -> Dict:
    """Create focused pathway interaction documents."""
    drug_title = drug_name.replace('_', ' ').title()

    if drug_name == "metformin":
        content = f"Metformin and AMPK Signaling Pathway\n\n"
        content += "Metformin activates AMP-activated protein kinase (AMPK), a central regulator of cellular energy homeostasis. "
        content += "AMPK activation inhibits hepatic gluconeogenesis by downregulating key enzymes including PEPCK and G6Pase. "
        content += "In peripheral tissues, AMPK enhances glucose uptake through GLUT4 translocation and improves insulin sensitivity. "
        content += "The pathway also affects lipid metabolism by inhibiting fatty acid synthesis and promoting fatty acid oxidation. "
        content += "This multi-target action explains metformin's effectiveness in Type 2 Diabetes management."

    elif drug_name == "lisinopril":
        content = f"Lisinopril and Renin-Angiotensin-Aldosterone System\n\n"
        content += "Lisinopril inhibits angiotensin-converting enzyme (ACE), blocking the conversion of angiotensin I to angiotensin II. "
        content += "Angiotensin II is a potent vasoconstrictor that stimulates aldosterone secretion, sodium reabsorption, and sympathetic activity. "
        content += "By reducing angiotensin II levels, lisinopril causes vasodilation, decreased aldosterone secretion, and reduced blood volume. "
        content += "Additionally, ACE inhibition prevents bradykinin breakdown, contributing to vasodilation and potential cough side effects. "
        content += "This dual mechanism provides comprehensive blood pressure control and organ protection."

    elif drug_name == "canagliflozin":
        content = f"Canagliflozin and Renal Glucose Handling\n\n"
        content += "Canagliflozin inhibits sodium-glucose cotransporter 2 (SGLT2) in the proximal renal tubule, blocking glucose and sodium reabsorption. "
        content += "Under normal conditions, SGLT2 reabsorbs approximately 90% of filtered glucose. Inhibition increases urinary glucose excretion by 60-80g daily, "
        content += "lowering blood glucose through an insulin-independent mechanism. The concomitant natriuresis and osmotic diuresis contribute to "
        content += "blood pressure reduction and weight loss. These hemodynamic effects also provide cardiovascular and renal protection benefits "
        content += "beyond glycemic control alone."

    else:
        content = f"{drug_title} Pathway Interactions\n\n"
        content += f"{drug_info['mechanism']} The drug primarily affects the {drug_info['pathway']} pathway, "
        content += "modulating key physiological processes to achieve therapeutic effects."

    return {
        "doc_id": f"drug_pathway_{drug_name}",
        "doc_type": "content",
        "content": content.strip()
    }


def create_class_comparison_documents() -> List[Dict]:
    """Create drug class comparison documents."""
    documents = []

    # ACE inhibitors comparison
    ace_content = """ACE Inhibitors Drug Class Comparison

Angiotensin-converting enzyme (ACE) inhibitors are a class of medications used primarily for hypertension and heart failure. Common ACE inhibitors include:

- Lisinopril: Long-acting, primarily renally eliminated
- Enalapril: Prodrug converted to enalaprilat, hepatic metabolism
- Ramipril: Long half-life active metabolite, cardiovascular protection
- Captopril: Short-acting, contains sulfhydryl group

All ACE inhibitors share the mechanism of blocking angiotensin II production, but differ in pharmacokinetics, tissue penetration, and specific indications. They are first-line therapy for hypertension, especially in patients with diabetes or heart failure due to their renal protective effects."""

    documents.append({
        "doc_id": "drug_class_ace_inhibitors",
        "doc_type": "content",
        "content": ace_content.strip()
    })

    # Statins comparison
    statin_content = """Statins (HMG-CoA Reductase Inhibitors) Drug Class

Statins are lipid-lowering medications that inhibit HMG-CoA reductase, the rate-limiting enzyme in cholesterol synthesis. Common statins include:

- Atorvastatin: Potent, primarily metabolized by CYP3A4
- Simvastatin: Moderate potency, significant drug interactions
- Rosuvastatin: Highly potent, minimal CYP metabolism
- Pravastatin: Less potent, hydrophilic, fewer drug interactions

Statins reduce LDL cholesterol by 20-60% depending on dose and specific agent. They also provide pleiotropic benefits including plaque stabilization, anti-inflammatory effects, and endothelial function improvement. These effects contribute to significant cardiovascular risk reduction beyond lipid lowering alone."""

    documents.append({
        "doc_id": "drug_class_statins",
        "doc_type": "content",
        "content": statin_content.strip()
    })

    # SGLT2 inhibitors comparison
    sglt2_content = """SGLT2 Inhibitors Drug Class Overview

Sodium-glucose cotransporter 2 (SGLT2) inhibitors represent a novel class of diabetes medications with cardiovascular and renal benefits. Key agents include:

- Canagliflozin: Also inhibits SGLT1 at higher doses
- Empagliflozin: Strong cardiovascular outcome data
- Dapagliflozin: Approved for heart failure and chronic kidney disease
- Ertugliflozin: Newer agent with similar efficacy

SGLT2 inhibitors lower blood glucose by increasing urinary glucose excretion. Beyond glycemic control, they provide significant benefits including blood pressure reduction, weight loss, cardiovascular death reduction, and slowed progression of diabetic kidney disease. These multi-system benefits have transformed diabetes management paradigms."""

    documents.append({
        "doc_id": "drug_class_sglt2_inhibitors",
        "doc_type": "content",
        "content": sglt2_content.strip()
    })

    return documents


def save_documents(documents: List[Dict], output_file: Path):
    """Save documents in JSONL format."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + '\n')

    print(f"Saved {len(documents)} drug mechanism documents to {output_file}")


def main():
    """Main execution function."""
    print("Starting drug mechanism information compilation...")

    # Create all drug mechanism documents
    print("Creating individual drug mechanism documents...")
    drug_docs = create_drug_mechanism_documents()
    print(f"Created {len(drug_docs)} individual drug documents")

    # Create drug class comparison documents
    print("Creating drug class comparison documents...")
    class_docs = create_class_comparison_documents()
    print(f"Created {len(class_docs)} drug class documents")

    # Combine all documents
    all_documents = drug_docs + class_docs
    print(f"Total documents: {len(all_documents)}")

    # Save documents
    save_documents(all_documents, OUTPUT_FILE)

    print("\n✅ Drug mechanism information compilation completed successfully!")
    print(f"📊 Generated {len(all_documents)} comprehensive drug documents")
    print(f"📁 Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()