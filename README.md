# Enable Banking — liczniki płatności dla Home Assistant OS

Wersja 0.1.9, prototyp do weryfikacji na rzeczywistych danych bankowych.
Nie jest oficjalną integracją banków ani Enable Banking.

## Instalacja przez HACS

1. W HACS otwórz menu → Własne repozytoria (Custom repositories).
2. Dodaj `https://github.com/pawelczykkacper/easyBanking` z typem **Integration**.
3. Wyszukaj **Easy Banking**, pobierz najnowsze wydanie **v0.1.9** i zrestartuj HA.
4. Kontynuuj od kroku 2 instrukcji poniżej (klucz, adres powrotu i konfiguracja).

Jeżeli HACS pokazuje błąd dla starego identyfikatora `35ea96b`, otwórz stronę
repozytorium w HACS, użyj „Aktualizuj informacje” (Update information), a następnie
„Pobierz ponownie” (Redownload) i wybierz **v0.1.9**. Jeżeli repozytorium nie jest
jeszcze zainstalowane i nadal pokazuje starą wersję, usuń je tylko z listy HACS
i dodaj ponownie jako własne repozytorium typu Integration.

## Instalacja ręczna

1. Pobierz repozytorium (Code → Download ZIP) i rozpakuj. Skopiuj folder `custom_components/enable_banking` do
   `/config/custom_components/enable_banking` w Home Assistant (np. przez dodatek Samba).
   Nie kopiuj zewnętrznego folderu `enable_banking` jako dodatkowego poziomu.
2. Skopiuj swój klucz prywatny `.pem` do `/config/enable_banking.pem`.
   Nie umieszczaj go w `/config/www`, repozytorium ani w czacie.
   Kopie zapasowe HA zawierające klucz i ustawienia integracji przechowuj bezpiecznie.
3. W aplikacji **Production** w Enable Banking dodaj do dozwolonych adresów powrotu
   dokładnie `https://TWOJA-DOMENA-HA/api/enable_banking/callback`.
   Zachowaj też adresy używane przez inne aplikacje.
4. Uruchom ponownie Home Assistant.
5. Ustawienia → Urządzenia i usługi → Dodaj integrację → wyszukaj „Enable Banking”.
6. Podaj Application ID, ścieżkę `/config/enable_banking.pem` i adres
   `https://TWOJA-DOMENA-HA` (bez końcowej ścieżki).
7. Wybierz bank. Otwórz link autoryzacji w nowej karcie i zatwierdź zgodę w banku.
   Po powrocie zobaczysz instrukcję. Skopiuj cały adres z paska przeglądarki,
   wróć do formularza integracji i wklej go. Kod i state są sprawdzane lokalnie.
8. Zaznacz rachunki do liczenia. Powtórz dodawanie integracji dla każdego banku:
   Alior, VeloBank, Credit Agricole, Millennium, używając tego samego klucza i ID.
   Lista nazw pochodzi z API, nie jest wpisana na stałe.

## Cloudflare

Nie musisz podawać domeny autorowi integracji. Wpiszesz ją lokalnie w formularzu.
Callback musi być osiągalny w przeglądarce po autoryzacji. Jeżeli korzystasz z
Cloudflare Access, może być potrzebne zalogowanie do Access przed rozpoczęciem.
Nie wyłączaj ochrony całego Home Assistant. Endpoint callback nie wymaga logowania
HA, zwraca tylko stałą instrukcję, nie odczytuje danych bankowych i nie przetwarza
kodu. Dopiero zalogowany użytkownik wkleja adres do formularza konfiguracji.
Adres powrotu zawiera jednorazowy kod: nie udostępniaj go i nie publikuj logów URL.

## Co liczy integracja

Każdy bank ma sensory liczby płatności kartą i BLIK-iem oraz nierozpoznanych obciążeń.
Zamiast sensora łącznej liczby płatności integracja tworzy sensory sumy kwot płatności
za bieżący miesiąc, osobno dla każdej waluty (np. PLN i EUR). Kwoty w różnych
walutach nigdy nie są dodawane do siebie. Wybrane rachunki w obrębie banku są sumowane.

Uwzględnia tylko `BOOK` + `DBIT`, według daty księgowania (`booking_date`)
w bieżącym miesiącu kalendarzowym w strefie czasowej HA. Zdarzenia oczekujące,
uznania i zwroty nie zwiększają liczników. Pobiera wszystkie strony historii.
Odświeżanie: co 8 godzin, brak szybkich automatycznych ponowień. Duża historia
może zużyć kilka wywołań API podczas pojedynczego odświeżenia; limity ustala bank.
Błąd pobrania dowolnego wybranego rachunku oznacza niedostępność sensorów,
a nie częściowy wynik lub fałszywe zero. Po zmianie miesiąca stary wynik jest
niedostępny do kolejnego odświeżenia; możesz wywołać `homeassistant.update_entity`.

Rozpoznawanie jest ostrożną heurystyką na podstawie opisów. Płatność musi mieć
opis płatności/zakupu i oznaczenie karty albo BLIK; wyjątkiem jest opis zawierający
„Lidl”, rozpoznawany jako płatność kartą. Wypłaty, przelewy (w tym na telefon),
opłaty, anulowania, zwroty i „Zaokrąglenie przekazane z rachunku” są wykluczane.
Sam napis „BLIK” nie wystarcza.
Inne obciążenia trafiają do „Nierozpoznane obciążenia”. Nie są to wyłącznie
nierozpoznane płatności: mogą obejmować inne rodzaje obciążeń rachunku.

**Przed użyciem do pilnowania warunków bezpłatnego konta porównaj wyniki z historią
bankową. Nie zweryfikowano opisów z Twoich czterech banków. Heurystyka może
pominąć lub błędnie rozpoznać płatność.** Reguły banku, np. data wykonania zamiast
księgowania, mogą dać inny wynik. Nierozpoznane operacje pomagają wykryć braki,
ale zero takich operacji nie gwarantuje poprawności klasyfikacji.

## Odnowienie zgody

Po wygaśnięciu sesji Home Assistant poprosi o ponowną autoryzację. Wprowadź dane
aplikacji, wybierz ten sam bank, autoryzuj i ponownie wybierz rachunki.
Identyfikatory sensorów pozostaną zachowane. Błędy 401/403/404 także uruchamiają
ponowną autoryzację; mogą oznaczać problem z kluczem lub uprawnieniami, nie tylko
wygaśnięcie zgody.

## Prywatność i ograniczenia walidacji

Klucz nie jest zapisywany w konfiguracji wpisu: zapisywana jest jego ścieżka.
Wpis zawiera ID aplikacji, techniczne identyfikatory rachunków i sesji oraz datę
ważności zgody. Surowa historia jest przetwarzana w pamięci; opisy, salda i numery
kont nie trafiają do atrybutów sensorów ani logów integracji.

Sprawdzono składnię Pythona i testy logiki liczenia na danych syntetycznych.
Nie uruchomiono integracji w Home Assistant OS i nie wykonano autoryzacji na
rzeczywistych kontach. To wymaga Twojej instalacji, klucza oraz zgody w banku.

Dokumentacja: https://enablebanking.com/docs/api/quick-start/
Specyfikacja danych: https://enablebanking.com/docs/api/reference/

## Zgodność i testy

Poprawka 0.1.2 usuwa wymaganie PyJWT 2.10.1, które kolidowało z PyJWT 2.15.1
w Home Assistant Core 2026.10.4. Integracja korzysta z PyJWT dostarczanego przez
Core. Formularze korzystają z probatio, z fallbackiem do voluptuous w starszym HA.

Po aktualizacji przez HACS do v0.1.2 zrestartuj Home Assistant przed ponownym
otwarciem formularza. Jeśli pozostaje błąd 500, sprawdź pełny traceback
w Ustawienia → System → Dzienniki: sam kod HTTP nie identyfikuje przyczyny.

Testy logiki i pakowania: `python -B -m unittest discover -s tests -v`.
Testy formularzy wymagają zainstalowanego Home Assistant; bez niego są pomijane.
Testy obejmują serializację formularzy do formatu używanego przez frontend HA,
bez połączenia z rzeczywistym bankiem. Nie zastępują instalacji na HA OS.

## Poprawka listy banków (0.1.3)

Błąd `no_banks` przy aktywnej aplikacji mógł wynikać z nieprawidłowego filtra:
integracja sprawdzała `services` w obiektach banków, choć schemat ASPSPData
nie zawiera takiego pola. Wersja 0.1.9 wysyła `service=AIS` i `psu_type=personal`
bezpośrednio do `/aspsps?country=PL` i używa zwróconej listy bez tego filtra.
Po aktualizacji zrestartuj HA i ponów dodawanie integracji. Ponowne podłączanie
rachunków w panelu Enable Banking nie jest wymagane przez tę poprawkę.

## Diagnostyka połączenia (0.1.4)

Zamiast ogólnego `cannot_connect` formularz rozróżnia HTTP 401 (autoryzacja
aplikacji), HTTP 403 (uprawnienia), HTTP 429 (limit), niedozwolony adres powrotu,
niepoprawny format klucza, timeout, błąd sieci oraz nieoczekiwaną odpowiedź API.
Pozostałe błędy HTTP pokazują status i rozpoznany symboliczny kod Enable Banking.
Log integracji zawiera tylko etap, status HTTP i kod z zamkniętej listy lub nazwę
klasy wyjątku. Nie zapisuje treści błędu serwera, adresów, kluczy ani tokenów.

Po aktualizacji i restarcie HA ponów ten sam krok. Jeśli błąd pozostaje, przekaż
nowy komunikat i etap formularza. Nie trzeba ponownie podłączać kont w panelu EB.
Ta wersja poprawia diagnostykę; nie potwierdza przyczyny wcześniejszego błędu
`cannot_connect` i nie zmienia ustawień aplikacji po stronie Enable Banking.

## Brak linku do autoryzacji (0.1.5)

Integracja zawiera teraz kompletne `translations/en.json`, wymagane jako język
zapasowy dla integracji niestandardowej. Sam `strings.json` nie zapewnia tłumaczeń
w działającym HA. Polski interfejs nadal korzysta z `translations/pl.json`.

Po wybraniu banku formularz pokazuje także osobne pole z adresem autoryzacji.
Jeśli link w opisie jest niewidoczny, skopiuj adres z pierwszego pola i otwórz go
w nowej karcie. Nie wpisuj go w pole callback. Po zgodzie w banku skopiuj pełny
adres powrotu z `code` i `state` do drugiego pola. Pierwsze pole jest tylko do
kopiowania; zmiany jego zawartości nie wpływają na żądania API.

Po aktualizacji zrestartuj HA, odśwież stronę w przeglądarce i rozpocznij nową
konfigurację. Nie używaj adresu powrotu z wcześniejszej próby.

## Zakres historii i oczekująca autoryzacja (0.1.6)

Żądanie zgody do Enable Banking jawnie prosi o dostęp do historii (`transactions: true`).
Jeśli odpowiedź z `/sessions` wskazuje `PENDING_AUTHORIZATION`, HA pokaże osobną
informację o niedokończonym potwierdzeniu zamiast ogólnego błędu braku rachunków.
Log Enable Banking `PENDING_AUTHORIZATION` oznacza, że użytkownik musi dokończyć
autoryzację; puste `account_ids` są spodziewane przed jej zakończeniem.


## Icon

Source SVG for the piggy bank and coin icon: `custom_components/enable_banking/assets/piggy-bank.svg`.


## Sumy kwot płatności (0.1.7)

Sensor „Płatności razem” zastąpiono sensorami sumy kwot kwalifikowanych płatności
kartą i BLIK-iem, za bieżący miesiąc. Kwoty są grupowane według waluty transakcji;
przykładowo HA pokaże osobne sensory PLN i EUR. Suma obejmuje tylko zaksięgowane
obciążenia rozpoznane jako płatność kartą lub BLIK, z tymi samymi wykluczeniami
co liczniki. Przy dodawaniu transakcji w nowej walucie integracja utworzy sensor
tej waluty przy następnym odświeżeniu.


## Szczegóły nierozpoznanych obciążeń (0.1.8)

Dodano sensor tekstowy pokazujący datę i opis nierozpoznanych obciążeń. Atrybut
`transactions` zawiera do 100 wpisów z datą, opisem oraz kwotą i walutą, jeśli bank
je zwrócił. Nie zapisujemy identyfikatorów transakcji ani danych rachunku w sensorze.


## Klasyfikacja opisów „Operacja kartą” (0.1.9)

Opisy zawierające „operacja kartą” są rozpoznawane jako płatności kartą, nawet
jeśli nie zawierają słowa „płatność” lub „zakup”.

## Wykluczenie zaokrągleń i rozpoznawanie Lidl (0.1.10)

Wpisy z opisem „Zaokrąglenie przekazane z rachunku” są pomijane. Opis
zawierający „Lidl” jest rozpoznawany jako płatność kartą, także bez standardowego
oznaczenia karty.

## Waluta transakcji (0.1.11)

Jeśli bank zwróci dla transakcji walutę `XXX` albo nie poda waluty, integracja
używa waluty wybranego rachunku. Pozwala to prawidłowo sumować kwoty, gdy bank
nie oznacza waluty transakcji, a rachunek jest prowadzony w PLN.

## Rodzaj transakcji „Transakcja kartą debetową” (0.1.12)

Opisy rodzaju transakcji „Transakcja kartą debetową” są rozpoznawane jako
płatności kartą.
