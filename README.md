# WOK - Vocabulary Learning Web App

WOK is a vocabulary learning web app built with Flask, SQLite, and JavaScript. It is designed to help users collect new words quickly, review them with spaced repetition, and keep vocabulary learning lightweight enough to use every day.

## What the app does

- Lets users register, log in, and manage a personal learning profile
- Stores words, translations, review metadata, and optional context notes
- Uses flashcards and spaced repetition to schedule reviews
- Plays pronunciation audio with text-to-speech
- Supports a free practice mode for casual repetition
- Provides a searchable personal word list with deletion support

## Companion capture tool

The project also includes a companion app for word capture from a computer.

This tool is meant to make collection fast while reading or browsing. It can:

- capture words with hotkeys
- attach context automatically or manually
- send collected entries to the web app
- reduce friction when building a vocabulary list during the day

It is a helper workflow, not the main learning interface.

## Core features

- User registration, login, and logout
- Token-based account identification for the capture workflow
- Manual word entry with optional translation and context
- Automatic translation when no translation is provided
- Flashcard training with review scheduling
- Audio pronunciation for active cards
- Free mode for unscheduled practice
- Personal word library with search and delete actions
- SQLite storage with cascaded relationships

## How it works

1. A user creates an account.
2. The app stores a token in the profile page.
3. Words are added manually or through the capture workflow.
4. Each word receives a translation, optional context, and review metadata.
5. Flashcards show due words first.
6. After each answer, the review schedule is updated.
7. The user can return later and continue from the current review state.

## Spaced repetition model

The review system tracks:

- ease factor
- interval
- next review date
- learning stage
- repetitions
- lapses

Answer quality affects scheduling:

- Forgot
- Hard
- Normal
- Easy

This keeps the review flow simple while still giving each word a personalized schedule.

## Tech stack

- Python
- Flask
- SQLite
- JavaScript
- Bootstrap
- gTTS for audio pronunciation
- translators for automatic translation

## Project structure

- [app.py](app.py)
- [helpers.py](helpers.py)
- [schema.sql](schema.sql)
- [init_db.py](init_db.py)
- [templates/](templates)
- [static/](static)

## Database schema

### users

- id
- username
- password_hash
- token

### words

- id
- word
- translation
- language

### user_words

- id
- user_id
- word_id
- ease_factor
- interval
- next_review
- count
- learning
- repetitions
- lapses
- context

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Initialize the database.
4. Run the application.

Example:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python app.py
```

## Configuration

Environment variables:

- `SECRET_KEY` for Flask session security

Example:

```bash
set SECRET_KEY=your-secret-key
```

## Pages

- `/` - landing page
- `/register` - create a new account
- `/login` - sign in
- `/profile` - view token and switch mode
- `/add` - add a new word
- `/tasks` - choose a learning mode
- `/flashcards` - review due words
- `/my_words` - manage saved words

## Notes

- The app currently focuses on translation-based vocabulary learning.
- The free mode is useful for casual practice.
- The capture workflow is intended to make vocabulary collection fast during reading or browsing.

## Roadmap

These are planned improvements and ideas for the next version:

- Add better hover and shortcut interactions
- Add a production-ready release configuration
- Add a proper dependency file and pin versions
- Make statistics and counters fully functional
- Improve profile and nickname interaction
- Add reminders for overdue reviews
- Improve capture API behavior for context and hotkey workflows
- Polish the interface and release configuration

## Future ideas

- Better answer validation
- Typo tolerance with Levenshtein distance
- Synonym-based answer checking
- Definition mode in addition to translation mode
- Export and import vocabulary lists
- Mobile-friendly capture flow
- Background notifications or reminders

## About

This project started as a CS50 final project and was later shaped into a personal vocabulary learning tool.