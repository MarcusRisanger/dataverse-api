"""
A collection of Dataverse Complex Property metadata classes.
"""

from dataclasses import dataclass, field
from typing import overload

from dataverse.metadata.base import BASE_TYPE, MetadataBase
from dataverse.metadata.enums import AssociatedMenuBehavior, AssociatedMenuGroup, AttributeRequiredLevel, CascadeType


@dataclass
class RequiredLevel(MetadataBase):
    """
    Complex Property describing the Required Level of an Attribute.

    Parameters
    ----------
    value : AttributeRequiredLevel
        Enum designating the actual required level value for the Attribute.
    can_be_changed: bool
        Whether the setting can be changed.
    """

    value: AttributeRequiredLevel = AttributeRequiredLevel.NONE
    can_be_changed: bool = True
    managed_property_logical_name: str = field(init=False, default="canmodifyrequirementlevelsettings")


@dataclass
class LocalizedLabel(MetadataBase):
    """
    Complex property describing a Localized Label in Dataverse.
    Localized labels are associated with a Microsoft Locale ID (LCID)

    Parameters
    ----------
    label : str
        The text to be shown.
    language_code : int
        The associated language code for the specific localized label.
    """

    _odata_type: str = field(init=False, default=BASE_TYPE + "LocalizedLabel")
    label: str
    language_code: int = 1033


@dataclass
class Label(MetadataBase):
    """
    Complex property describing a Label in Dataverse.

    Parameters
    ----------
    localized_labels : list of `LocalizedLabels`
        The list of localized labels defined for the `Label`. Each
        `LocalizedLabel` defines the label for an associated language code.
    """

    _odata_type: str = field(init=False, default=BASE_TYPE + "Label")
    localized_labels: list[LocalizedLabel] = field(default_factory=list)


@overload
def create_label(*, label: str) -> Label:
    ...


@overload
def create_label(*, label: tuple[str, int]) -> Label:
    ...


@overload
def create_label(*, label: str, language_code: int) -> Label:
    ...


@overload
def create_label(*, labels: list[tuple[str, int]]) -> Label:
    ...


def create_label(
    *,
    label: str | tuple[str, int] | None = None,
    language_code: int | None = None,
    labels: list[tuple[str, int]] | None = None,
) -> Label:
    """
    Creates a new `Label` instance.

    Parameters
    ----------
    label : string or tuple of string and integer
        For creating one `LocalizedLabel` within the `Label`.
    code : int
        The language code for a given `label`.
    labels: tuple of string and integer
        For specifying multiple `LocalizedLabel`s within the `Label`.
        Each tuple represents one label/language code pair.

    Returns
    -------
    `Label`
        A metadata object according to Dataverse specification.

    Raises
    ------
    ValueError: If input types are incorrect.
    AssertionError: If tuples are incorrectly typed.
    """

    if language_code is None:
        language_code = 1033

    if isinstance(label, tuple):
        return Label([LocalizedLabel(label=label[0], language_code=label[1])])
    elif isinstance(label, str):
        return Label([LocalizedLabel(label, language_code)])
    elif isinstance(labels, list):
        assert all([isinstance(x[0], str) for x in labels]), "Labels should be strings!"
        assert all([isinstance(x[1], int) for x in labels]), "Language codes should be ints!"
        return Label([LocalizedLabel(*label) for label in labels])
    else:
        raise ValueError("Correct input was not provided.")


@dataclass
class AssociatedMenuConfiguration(MetadataBase):
    """
    Complex Property for Associated Menu Config.

    Parameters
    ----------
    behavior : AssociatedMenuBehavior
        Describes the behavior of the associated menu for a one-to-many relationship.
    group: AssociatedMenuGroup
        Describes the group in which to display the associated menu for an entity relationship.
    order : int
        The order for the associated menu. Value must be higher than 10 000.
    label : Label
        The label for the associated menu.
    """

    behavior: AssociatedMenuBehavior = AssociatedMenuBehavior.USE_COLLECTION_NAME
    group: AssociatedMenuGroup = AssociatedMenuGroup.DETAILS
    order: int = 10000
    label: Label = field(default_factory=lambda: create_label(label=""))


@dataclass
class CascadeConfiguration(MetadataBase):
    """
    Complex Property for Cascade Configuration.
    """

    assign: CascadeType = CascadeType.CASCADE
    delete: CascadeType = CascadeType.CASCADE
    merge: CascadeType = CascadeType.CASCADE
    reparent: CascadeType = CascadeType.CASCADE
    share: CascadeType = CascadeType.CASCADE
    unshare: CascadeType = CascadeType.CASCADE