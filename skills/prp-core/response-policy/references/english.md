# English: ASD-STE100 at 80%

ASD-STE100 (Simplified Technical English) is a controlled language written
for aircraft maintenance documents. Its full rules are strict: a dictionary
of about 900 approved words, each with one meaning and one part of speech.
A reply does not need the dictionary. It needs the structural rules, which
make text easier to read once and harder to misread.

"80%" means: apply the rules below, allow the project's technical names and
terms, and allow a longer word when no short one is exact. Do not check
words against the STE dictionary.

Official source: [asd-ste100.org](https://www.asd-ste100.org/about_STE.html).

## Sentences

- A step has 20 words or fewer. A descriptive sentence has 25 words or
  fewer. Treat a longer sentence as a prompt to check it, not a failure.
- Put one instruction in each sentence. Two actions stay together only when
  the user must do them at the same time.
- Write steps in the imperative: "Run the tests", not "The tests should be
  run".
- Use the active voice when the actor matters. Name the actor when the user
  could confuse a system action with their own.
- Use simple tenses: present, past, future. Avoid progressive and perfect
  forms where a simple form says the same thing.
- Keep a paragraph to one topic and six sentences or fewer.

## Words

- Use one word for one meaning, and one name for one thing. Do not vary a
  term to avoid repetition.
- Keep noun clusters to three words or fewer. Break a longer one with a
  preposition: "the timeout of the retry policy", not "retry policy timeout
  value setting".
- Keep "the", "a", and "this". Do not write telegraphically.
- Prefer the short common word:

| Avoid | Use |
| --- | --- |
| utilize, leverage | use |
| prior to | before |
| subsequent to | after |
| commence, initiate | start |
| terminate | stop, end |
| approximately | about |
| ensure | make sure |
| in order to | to |
| facilitate | help |
| in the event that | if |
| a number of | some, several, or the number |
| at this point in time | now |

## Safety and failure

- Put a warning before the step it guards. Give the command first, then the
  risk: "Do not force-push this branch. Two open PRs build on it."
- Put the condition before the action: "If the build fails, read the first
  error", not "Read the first error if the build fails".
- Say what failed, what it affects, and how to recover, in that order.

## Samples

Before: "It is imperative that the migration is verified prior to
commencing the deploy in order to ensure that no data is lost."

After: "Verify the migration before you start the deploy. An unverified
migration can lose data."

Check: two sentences, one instruction, the risk stated, no new detail.

Before: "Tests have been run and it was found that 3 are failing, which
might be related to the config change."

After: "3 tests fail. The config change might be the cause."

Check: the count and the "might" survive; the cause stays uncertain.

Before: "Retry policy timeout value configuration was updated."

After: "I changed the timeout in the retry policy."

Check: noun cluster broken, actor named, nothing added.

Before: "The PR is ready to merge."

After: "The PR is ready to merge."

Check: already clear. Do not rewrite clear text for variety.
