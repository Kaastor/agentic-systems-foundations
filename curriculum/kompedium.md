Oto skondensowane, techniczne kompendium źródeł, które spina klamrą wszystkie poruszone przez nas tematy: od mapowania RL na LLM, przez dynamiczny routing, aż po optymalizację produkcyjną.

Podzieliłem to na cztery filary kompetencji. Dla każdego źródła wylistowałem **Kluczowe Koncepty**, które tam znajdziesz – to Twoja "mapa drogowa".

---

### Filar 1: Architektura i Wzorce Projektowe (Fundament)

Tu dowiesz się, jak projektować grafy przejść i zarządzać przepływem sterowania (Control Flow).

**1. Anthropic Research: "Building Effective Agents"**

* **Typ:** Artykuł techniczny / Whitepaper
* **Dlaczego:** Biblia dla inżynierów w 2024/25. Definiuje słownik pojęć, którego używa branża.
* **Kluczowe Koncepty:**
* **Workflows vs Agents:** Kiedy stosować determinizm, a kiedy stochastyczność.
* **Routing:** Klasyfikacja intencji (Dynamic Routing) jako węzeł decyzyjny.
* **Orchestrator-Workers:** Wzorzec nadzorcy rozdzielającego zadania.
* **Evaluator-Optimizer:** Pętla sprzężenia zwrotnego (Feedback Loop).



**2. Lilian Weng (OpenAI): "LLM Powered Autonomous Agents"**

* **Typ:** Deep-dive Blog Post
* **Dlaczego:** Najlepsze teoretyczne zmapowanie komponentów agenta.
* **Kluczowe Koncepty:**
* **Memory Systems:** Sensory Memory, Short-term (Context), Long-term (Vector DB).
* **Planning:** Decomposition (Chain of Thought), Self-Reflection.
* **Tool Use:** Funkcje API jako Action Space.



---

### Filar 2: RL w Agencie & Algorytmy Przeszukiwania (Twój "Core")

Tu Twoja wiedza o RL spotyka się z LLM. Źródła te traktują o "myśleniu" modelu.

**3. Paper: "Language Agent Tree Search (LATS)" (Zhou et al.)**

* **Typ:** Publikacja naukowa (Arxiv)
* **Dlaczego:** Bezpośrednie przeniesienie **MCTS (Monte Carlo Tree Search)** do LLM.
* **Kluczowe Koncepty:**
* **State Evaluation:** Wycena stanu przez model (Value Function).
* **Backpropagation:** Propagacja błędu w górę drzewa myśli.
* **Exploration vs Exploitation:** Generowanie alternatywnych rozwiązań w czasie inferencji.



**4. Paper: "Reflexion: Language Agents with Verbal Reinforcement Learning" (Shinn et al.)**

* **Typ:** Publikacja naukowa (Arxiv)
* **Dlaczego:** Wyjaśnia, jak zastąpić aktualizację wag (Gradient Descent) aktualizacją pamięci (Context Update).
* **Kluczowe Koncepty:**
* **Verbal Reinforcement:** Tekstowa informacja zwrotna zamiast skalarnej nagrody.
* **Self-Correction:** Mechanizm pętli naprawczej.
* **Episodic Memory:** Zapamiętywanie błędów z przeszłości, by ich nie powielać (Policy Improvement).



**5. Paper: "Tree of Thoughts (ToT)" (Yao et al.)**

* **Typ:** Publikacja naukowa (Arxiv)
* **Dlaczego:** Fundament dla modeli typu OpenAI o1.
* **Kluczowe Koncepty:**
* **Search Algorithms:** BFS (Breadth-First Search) i DFS (Depth-First Search) w przestrzeni tokenów.
* **State Generation:** Generowanie  kandydatów na następny krok.



---

### Filar 3: Optymalizacja i Inżynieria (DSPy & Evals)

Podejście programistyczne do optymalizacji promptów (najbliższe "uczeniu" w RL).

**6. Stanford NLP: DSPy (Documentation & Papers)**

* **Typ:** Framework / Dokumentacja / Paper
* **Dlaczego:** Traktuje prompty jak parametry do optymalizacji, a nie tekst do pisania ręcznego.
* **Kluczowe Koncepty:**
* **Teleprompters:** Optymalizatory, które "uczą się" najlepszych promptów na podstawie metryk (bootstrap few-shot).
* **Signatures:** Abstrakcja wejścia/wyjścia (analogia do definicji funkcji).
* **Metric-Driven Development:** Budowanie systemów w oparciu o twarde dane, a nie "czuja".



**7. Eugene Yan: "Systematic Evals"**

* **Typ:** Blog inżynierski
* **Dlaczego:** O tym, jak mierzyć sukces, gdy nie masz "Ground Truth" (Labeli).
* **Kluczowe Koncepty:**
* **LLM-as-a-Judge:** Używanie modelu do oceny innego modelu (Reward Model).
* **Reference-free evaluation:** Ocenianie jakości bez wzorcowej odpowiedzi.



---

### Filar 4: Implementacja Stanowa (State Machines)

Narzędzia, w których zaimplementujesz grafy i stany.

**8. LangGraph (Documentation & Concepts)**

* **Typ:** Dokumentacja techniczna
* **Dlaczego:** Standard implementacji cyklicznych grafów stanów w Pythonie.
* **Kluczowe Koncepty:**
* **State Schema:** Definicja struktury danych (Pydantic/TypedDict) przesyłanej między węzłami.
* **Conditional Edges:** Dynamiczne przejścia sterowane logiką lub LLM-em.
* **Checkpointing:** Persistence warstwy pamięci (umożliwia "Time Travel" i debugging).
* **Human-in-the-loop:** Przerywanie grafu w celu interwencji człowieka.



---

### Jak to połączyć? (Twoja ścieżka rozwoju)

Jako Senior Dev + RL Expert, sugeruję taką kolejność konsumpcji:

1. Przeczytaj **"Building Effective Agents"** (Anthropic), aby zrozumieć, co budujesz.
2. Przestudiuj **LangGraph Concepts**, aby zrozumieć, jak to oprogramować (State + Graph).
3. Przeczytaj paper **Reflexion** lub **LATS**, aby zrozumieć, jak zaimplementować pętlę "uczenia" (Self-Correction/Search).
4. Wdróż się w **DSPy**, aby zautomatyzować optymalizację tego systemu (zamiast ręcznie poprawiać prompty).

To zestawienie pokrywa 100% potrzebnej wiedzy, by wejść na poziom Expert w Agentic AI.