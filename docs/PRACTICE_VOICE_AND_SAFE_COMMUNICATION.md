# Practice engagement and communication guardrails

Prepared October 27, 2026. This describes application behaviour, not Safe Sport certification.

## Communication rules requested by the owner

| Sender | Ordinary messages |
| --- | --- |
| Athlete | Coaches/head coaches available to them; never directors |
| Parent | Coaches of approved linked athletes, and the gym director |
| Coach/head coach | Director, permitted gym parents and staff, and supervised athlete threads |
| Director | Parents and staff; no direct athlete conversations |

All athlete accounts use the supervised route. The app does not infer adulthood from an incomplete date of birth. New athlete-coach threads require the sender to select an approved linked parent or a second active coach/head coach in the same gym. Directors cannot be the observer of an athlete thread. The observer's role/relationship and current gym membership are validated server-side. A staff role does not prove that a person is an adult, screened or trained; the gym must verify those requirements.

The composer explains that selected participants can read the entire new thread. Thread headers list the participants and observer. Existing one-to-one athlete threads remain accessible to their original authorized participants as read-only history. New observers are never silently added to earlier messages.

Observer removal, inactive membership or revoked parent approval blocks further supervised replies. Revoked parents lose access to related threads and message previews in the bell, inbox and recent-conversation cards. Cross-gym access is denied. Parent/coaching assignments include active training-group assignments as well as direct assignments.

Quick-message drafts missing an observer are preserved in the full composer. Announcements involving athletes require an explicitly selected second coach; the whole send is atomic. Directors' announcements reach permitted parents/staff, not athletes. Existing adult-only parent/coach/director routes remain available.

No automatic external email, safety report or participant message has been sent by this development work. Tests use fictional accounts in isolated databases.

## Practice engagement

The existing Practice Passport keeps its badge definitions, coach approval and earned history. New optional practice quest cards bring Ask & Learn, Great Teammate and private reflection into the athlete home page and passport. These are prompts to try within the agreed training plan, not automatic rewards for extra volume or a disclosure.

The athlete-home wellness survey streak tile is replaced by a Passport link. Attendance targets are no longer selected as the next suggested Passport adventure; existing attendance stamps and records are retained. Breaks do not reset earned stamps. Passport eligibility does not use wellness answers, messages, journals or safety reports. Saving a check-in or sending a message does not award a stamp.

Coach award guidance asks for positive recognition within the agreed practice plan, and cautions against using shared badge notes for private health or safety concerns. Journal privacy and sharing choices are unchanged.

## Support outside a shared conversation

`/safety/` is available without login and linked from the app navigation, public footer, messaging pages and daily check-in. It separates ordinary practice questions from concerns about a coach, director, parent or other adult. It does not collect allegations, forward a report, notify an implicated person or promise anonymity/confidentiality in ordinary app messages.

The page links directly to official provincial/national resources and explains that jurisdiction varies. A child or parent need not message the coach/director first to access those resources. It identifies app messaging as unsuitable for emergencies and does not pretend that the club director is an independent reporting body.

Sources checked October 27, 2026:

- Coaching Association of Canada, Rule of Two: https://coach.ca/sport-safety/responsible-coaching-movement/rule-two
- CAC electronic communications resource: https://coach.ca/resource/rcm-electronic-communications-and-social-media-use-guidelines
- Gymnastics Ontario Safe Sport resource portal: https://www.gymnasticsontario.ca/safe-sport/ (official search listing verified; full portal text was not retrievable during development)
- Sport Integrity Canada, reporting and scope: https://sportintegrity.ca/report-safe-sport

The CAC guidance calls for transparent communication and discourages one-to-one electronic contact. The app's named-observer and read-only legacy rules are an implementation choice informed by that guidance, not an assertion that the software alone fulfills an organization's policies or legal obligations. CSSP scope does not automatically cover every local club matter.

## Review file

`practice-voice-review.html` is a self-contained preview of the actual athlete home, Passport, athlete-to-coach composer, coach-to-director composer and public support page. It uses fictional local records; forms and scripts are disabled. It is a review file, not the deployed app.

## Migration and release

`communications.0004_conversation_requires_supervision_and_more` adds a flag and nullable observer reference to conversations. Existing participants, messages, surveys, practice records and earned stamps are not rewritten, deleted or automatically shared. Run migrations and static collection with the normal deployment process.

The operator still needs to verify applicable club/provincial policy, trained/screened adult eligibility, consent, response responsibilities and the correct reporting channels for the actual gym. The unfinished operator/retention details in the existing privacy notice remain outstanding; this change does not certify policy compliance.

## Validation

128 relevant application tests passed on Django 6.1: accounts, athletes, parents, communications, coaches, practice progress/journals and surveys. Coverage includes explicit observer selection, exact audiences, blocked director-athlete routes in both directions, parent and coach access to directors, preserved legacy history, revoked-parent previews, cross-gym isolation, CSRF, escaped content, group coach assignments and no reward from wellness/message activity.

System checks, static collection and migration consistency checks pass. No messages to real athletes, parents or staff are needed for verification. After deployment, check public welcome/support pages and normal sign-in routes; authenticated multi-role scenarios are exercised with the isolated synthetic test suite.
