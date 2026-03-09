# Паттерны промптов (ролевые)

> Источник: https://github.com/f/prompts.chat (180+ ролей)

## Формат паттерна

```
"Act as [Role]. I want you to [task]. You should [constraints]. My first request is [input]."
```

Ключевые элементы:
1. **Роль** — кем притворяться (Linux Terminal, Code Reviewer, Architect)
2. **Задача** — что делать (review code, generate tests, translate)
3. **Ограничения** — формат, стиль, границы (only respond with code, no explanations)
4. **Первый запрос** — конкретный input для начала работы

## Категории ролей (180+)

### Разработка и IT
- Linux Terminal, JavaScript Console, Python Interpreter, SQL Terminal
- Code Reviewer, UX/UI Developer, Senior Frontend Developer, Fullstack Developer
- IT Expert, IT Architect, Cyber Security Specialist, Machine Learning Engineer
- Software QA Tester, Tech Reviewer, RegEx Generator, SVG Designer
- Commit Message Generator, Unit Tester Assistant

### Написание и контент
- Novelist, Screenwriter, Poet, Tech Writer, Essay Writer, Journalist
- Storyteller, Plagiarism Checker, Proofreader, Title Generator
- Cover Letter, Elocutionist, Commentariat

### Образование
- Math Teacher, Philosophy Teacher, AI Writing Tutor
- Debate Coach, Public Speaking Coach, Educational Content Creator
- Speech-Language Pathologist, Literary Critic, Note-Taking Assistant

### Бизнес и карьера
- CEO, Project Manager, Product Manager, Career Coach
- Job Interviewer, Recruiter, Startup Idea Generator
- Financial Analyst, Investment Manager, Accountant, Salesperson
- Real Estate Agent, Logistician, Startup Tech Lawyer

### Креатив
- Movie Critic, Standup Comedian, Advertiser, Social Media Manager
- Music Composer, Midjourney Prompt Generator
- Text Based Adventure Game, Chess Player

### Языки
- English Translator, Synonym Finder, Emoji Translator
- Language Detector, Etymology Expert, Biblical Translator

### Здоровье и лайфстайл
- Personal Trainer, Dietitian, Chef, Psychologist
- Mental Health Adviser, Interior Decorator, Personal Stylist

### Утилиты
- Password Generator, Smart Domain Name Generator
- Prompt Generator, Prompt Enhancer, Diagram Generator
- Fill in the Blank Worksheets Generator

## Применимые паттерны для наших проектов

### Для Claude Code агентов
- **Code Reviewer** → уже есть как агент
- **IT Architect** → уже есть как агент (architect)
- **Software QA Tester** → tdd-guide агент
- **Commit Message Generator** → git-workflow правила

### Для Survey Automation (1С)
- **Project Manager** → шаблон для планирования обследований
- **Business Analyst** → сбор требований, GAP-анализ
- **Tech Writer** → документация процессов

### Для промпт-инжиниринга
- **Prompt Generator** → создание промптов для новых скиллов
- **Prompt Enhancer** → улучшение существующих промптов

## Полезные техники из коллекции

1. **Boundary setting** — чёткие границы что модель НЕ делает
2. **Output format lock** — "respond only with X, no explanations"
3. **Persona depth** — детальное описание экспертизы роли
4. **First request pattern** — сразу давать конкретный input
5. **Negative constraints** — "do not break character", "never explain"
