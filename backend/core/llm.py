from datetime import date, datetime

from .config import settings
from .rag import _openai


def _build_patient_context(patient, medications: list) -> str:
    age = (date.today() - patient.date_of_birth).days // 365

    lines = [
        f"Name: {patient.name}",
        f"Age: {age} years",
        f"Gender: {patient.gender}",
        f"Blood Group: {patient.blood_group or 'Unknown'}",
        f"Allergies: {', '.join(patient.allergies) if patient.allergies else 'None reported'}",
        f"Past Diseases: {', '.join(patient.past_diseases) if patient.past_diseases else 'None reported'}",
        f"Past Surgeries: {', '.join(patient.past_surgeries) if patient.past_surgeries else 'None reported'}",
        f"Family History: {patient.family_history or 'Not provided'}",
    ]

    if medications:
        med_lines = [
            f"  - {m.medicine_name} {m.dosage}, {m.frequency}"
            + (f" (since {m.start_date})" if m.start_date else "")
            for m in medications if m.is_current
        ]
        lines.append("Current Medications:\n" + "\n".join(med_lines) if med_lines else "Current Medications: None")
    else:
        lines.append("Current Medications: None")

    return "\n".join(lines)


def _build_knowledge_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant medical literature retrieved from the knowledge base."

    sections = []
    for i, chunk in enumerate(chunks, 1):
        author_part = f", {chunk['author']}" if chunk.get("author") else ""
        sections.append(
            f"[{i}] Source: {chunk['book_title']}{author_part}, Page {chunk['page_number']}\n"
            f"{chunk['chunk_text']}"
        )
    return "\n\n".join(sections)


def generate_diagnosis_suggestion(
    patient,
    medications: list,
    retrieved_chunks: list[dict],
    doctor_query: str,
) -> str:
    patient_context = _build_patient_context(patient, medications)
    knowledge_context = _build_knowledge_context(retrieved_chunks)

    system_prompt = (
        "You are an AI medical assistant supporting a licensed doctor. "
        "Your role is strictly advisory — you provide analysis and suggestions "
        "based on the patient's data and medical literature, but the doctor always "
        "makes the final clinical decision. "
        "Be precise, cite your sources using [Source N] notation, and clearly state "
        "when your confidence is limited. Never make a definitive diagnosis."
    )

    user_prompt = f"""PATIENT INFORMATION:
{patient_context}

RELEVANT MEDICAL LITERATURE:
{knowledge_context}

DOCTOR'S QUERY:
{doctor_query}

Provide a structured advisory analysis:
1. Key observations from the patient data relevant to this query
2. Analysis based on the medical literature (cite sources as [Source N])
3. Possible considerations for the doctor to evaluate
4. Any red flags or urgent concerns to address

End with: "Note: This is an AI-generated advisory. The treating physician must make all clinical decisions."
"""

    response = _openai().chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    return response.choices[0].message.content


def answer_patient_query(patient, medications: list, lab_results: list, diagnoses: list, question: str) -> str:
    """Strictly answers from doctor-entered data only. Redirects any diagnostic/medical advice question."""
    age = (date.today() - patient.date_of_birth).days // 365

    med_lines = "\n".join(
        f"- {m.medicine_name} {m.dosage}, {m.frequency}" + (f" (ongoing)" if m.is_current else f" (ended {m.end_date})")
        for m in medications
    ) or "None on record"

    lab_lines = "\n".join(
        f"- {l.test_name}: {l.result_value}{' ' + l.unit if l.unit else ''} on {l.test_date}"
        + (" [flagged as abnormal]" if l.is_abnormal else "")
        for l in lab_results
    ) or "None on record"

    diag_lines = "\n".join(
        f"- {d.decided_at.strftime('%Y-%m-%d') if d.decided_at else 'Pending'}: {d.final_diagnosis or 'Awaiting doctor decision'}"
        for d in diagnoses if d.decision in ("accepted", "modified")
    ) or "None on record"

    system_prompt = (
        "You are a patient information assistant for a medical clinic. "
        "Your ONLY role is to help patients retrieve information from their own medical records as entered by their doctor. "
        "STRICT RULES: "
        "1. Only answer from the patient data provided — never add medical knowledge. "
        "2. NEVER diagnose, interpret symptoms, suggest treatment, or recommend changes to medication. "
        "3. If asked anything medical beyond what's in their records, respond: "
        "'For medical questions, please consult your doctor directly.' "
        "4. Be friendly, clear, and brief."
    )

    user_prompt = f"""PATIENT RECORDS FOR: {patient.name} (Age {age}, {patient.gender})

ALLERGIES: {', '.join(patient.allergies) if patient.allergies else 'None on record'}

CURRENT & PAST MEDICATIONS:
{med_lines}

LAB RESULTS:
{lab_lines}

DIAGNOSES (doctor-confirmed):
{diag_lines}

Patient's question: {question}"""

    response = _openai().chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=600,
    )
    return response.choices[0].message.content
