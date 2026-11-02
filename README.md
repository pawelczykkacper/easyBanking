# Enable Banking — liczniki płatności dla Home Assistant OS

Wersja 0.1.2, prototyp do weryfikacji na rzeczywistych danych bankowych.
Nie jest oficjalną integracją banków ani Enable Banking.

## Instalacja przez HACS

1. W HACS otwórz menu → Własne repozytoria (Custom repositories).
2. Dodaj `https://github.com/pawelczykkacper/easyBanking` z typem **Integration**.
3. Wyszukaj **Easy Banking**, pobierz najnowsze wydanie **v0.1.2** i zrestartuj HA.
4. Kontynuuj od kroku 2 instrukcji poniżej (klucz, adres powrotu i konfiguracja).

Jeżeli HACS pokazuje błąd dla starego identyfikatora `35ea96b`, otwórz stronę
repozytorium w HACS, użyj „Aktualizuj informacje” (Update information), a następnie
„Pobierz ponownie” (Redownload) i wybierz **v0.1.2**. Jeżeli repozytorium nie jest
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

Każdy bank ma 4 sensory: płatności kartą, płatności BLIK, ich łączną liczbę
oraz nierozpoznane obciążenia. Wybrane rachunki w obrębie banku są sumowane.
Suma oznacza liczbę płatności, nie sumę pieniędzy.

Uwzględnia tylko `BOOK` + `DBIT`, według daty księgowania (`booking_date`)
w bieżącym miesiącu kalendarzowym w strefie czasowej HA. Zdarzenia oczekujące,
uznania i zwroty nie zwiększają liczników. Pobiera wszystkie strony historii.
Odświeżanie: co 8 godzin, brak szybkich automatycznych ponowień. Duża historia
może zużyć kilka wywołań API podczas pojedynczego odświeżenia; limity ustala bank.
Błąd pobrania dowolnego wybranego rachunku oznacza niedostępność sensorów,
a nie częściowy wynik lub fałszywe zero. Po zmianie miesiąca stary wynik jest
niedostępny do kolejnego odświeżenia; możesz wywołać `homeassistant.update_entity`.

Rozpoznawanie jest ostrożną heurystyką na podstawie opisów. Płatność musi mieć
opis płatności/zakupu i oznaczenie karty albo BLIK. Wypłaty, przelewy (w tym na
telefon), opłaty, anulowania i zwroty są wykluczane. Sam napis „BLIK” nie wystarcza.
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
