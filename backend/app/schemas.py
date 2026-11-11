"""Request schemas. Bad input is rejected here, before any pipeline step runs."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

TEXT_MAX_LEN = 100
NOTE_MAX_LEN = 2000

ShortText = Annotated[str, Field(min_length=1, max_length=TEXT_MAX_LEN)]
NoteText = Annotated[str, Field(min_length=1, max_length=NOTE_MAX_LEN)]
# allow_inf_nan=False rejects NaN and +/-inf. Out-of-limit values are allowed:
# the plain-code limit check turns them into a no_go verdict.
Reading = Annotated[float, Field(allow_inf_nan=False)]


class ReportIn(BaseModel):
    """A report as filed by an engineer."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: ShortText
    station: ShortText
    wind_knots: Reading
    temp_c: Reading
    fuel_pct: Reading
    note: NoteText
