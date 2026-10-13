import urllib.request, json, time

papers = [
    ('TutorLLM', 'TutorLLM: Customizing Learning Recommendations with Knowledge Tracing and Retrieval-Augmented Generation'),
    ('LPITutor', 'LPITutor: An LLM-Based Personalized Intelligent Tutoring System Using RAG and Prompt Engineering'),
    ('SRLAgent', 'SRLAgent: Enhancing Self-Regulated Learning Skills through Gamification and LLM Assistance'),
    ('Tong_Ren', 'Deep Knowledge Tracing and Cognitive Load Estimation for Personalized Learning Path Generation'),
    ('Ozkaya_VR', 'How LLMs Are Shaping the Future of Virtual Reality'),
    ('Ishaq_Review', 'Level Up Your Coding: A Systematic Review of Personalized, Cognitive, and Gamified Learning in Programming Education'),
    ('Wang_Agents', 'LLM Agents for Education: Advances and Applications'),
    ('Wilschut_Games', 'Agentic Knowledge Tracing: A Multi-Agent LLM Architecture for Stealth Assessment in Serious Games'),
    ('Muddaluru_CodeBERT', 'Code Quality Assessment Using Transformers'),
    ('Rumble_LEA', 'Learning Engagement Assistant LEA Cross-Course Scalability of an Agentic AI Tutoring System'),
    ('Xu_DKVMN', 'DKVMN+MRI: A New Deep Knowledge Tracing Model Based on DKVMN Incorporating Multi-Relational Information'),
    ('Costa_Gamified', 'Integrating LLMs in Gamified Systems: A Mathematical Framework'),
    ('Koskinen_Ethics', 'Game-Based Learning Can Enhance Students Understanding of AI Ethics'),
    ('Spriggs_LMS', 'Personalizing Education through an Adaptive LMS with Integrated LLMs'),
    ('Wang_EduPlanner', 'EduPlanner: LLM-Based Multi-Agent Systems for Customized Instructional Design'),
    ('Hu_SPARC', 'WIP: Enhancing Game-Based Learning with AI-Driven Peer Agents SPARC'),
    ('Shao_EDF', 'Evidence-Decision-Feedback: Theory-Driven Adaptive Scaffolding for LLM Agents'),
    ('Shi_Denoising', 'Denoising Programming Knowledge Tracing with a Code Graph-Based Tuning Adaptor'),
    ('Muddaluru_Score', 'CodeBERTScore: Evaluating Code Generation with Pretrained Models'),
    ('Zhang_Classroom', 'Evolution of AI in Education: Agentic Workflows and Classroom Simulation')
]

results = {}
for key, title in papers:
    url = 'https://api.crossref.org/works?query.title=' + urllib.parse.quote(title) + '&rows=1'
    req = urllib.request.Request(url, headers={'User-Agent': 'CodeQuestReport/1.0 (mailto:test@example.com)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data['message']['items']
            if items:
                it = items[0]
                results[key] = {
                    'query_title': title,
                    'found_title': it.get('title', [''])[0],
                    'doi': it.get('DOI', ''),
                    'container': it.get('container-title', [''])[0] if it.get('container-title') else '',
                    'year': it.get('issued', {}).get('date-parts', [[None]])[0][0],
                    'author': it.get('author', [])
                }
                print(f"[OK] {key} -> {results[key]['found_title'][:40]} | DOI: {results[key]['doi']}")
            else:
                results[key] = {'error': 'Not found'}
                print(f"[NONE] {key}")
    except Exception as e:
        results[key] = {'error': str(e)}
        print(f"[ERR] {key}: {e}")
    time.sleep(0.3)

with open(r'D:\CodeQuestAI\College Report\crossref_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)
print("Done saving Crossref verification results.")
