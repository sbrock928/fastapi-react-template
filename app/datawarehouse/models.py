"""Database models for the datawarehouse module (data warehouse database)."""

from sqlalchemy import Column, Integer, String, Float, SmallInteger, ForeignKey, CHAR, and_, Numeric,  DateTime, LargeBinary, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column, foreign
from sqlalchemy.dialects.mssql import MONEY
from sqlalchemy.sql import func
from app.core.database import DWBase as Base


class Deal(Base):
    """Deal model for securities stored in data warehouse."""

    __tablename__ = "deal"

    dl_nbr = Column(Integer, primary_key=True)
    issr_cde = Column(CHAR(12), nullable=False)
    cdi_file_nme = Column(CHAR(8), nullable=False)
    CDB_cdi_file_nme = Column(CHAR(10), nullable=True)

    tranches = relationship("Tranche", back_populates="deal")

    # Add relationship to CDI variables
    cdi_variables = relationship(
        "DealCdiVarRpt", 
        back_populates="deal",
        cascade="all, delete-orphan"
    )
    
    # Add relationship to Deal attributes
    attributes = relationship(
        "DealAttr",
        back_populates="deal",
        cascade="all, delete-orphan"
    )
    
    def get_cdi_variables_for_cycle(self, cycle_code: int):
        '''Get all CDI variables for this deal and cycle'''
        return [var for var in self.cdi_variables if var.cycle_cde == cycle_code]
    
    def get_cdi_variable_value(self, variable_name: str, cycle_code: int) -> float:
        '''Get a specific CDI variable value for this deal and cycle'''
        for var in self.cdi_variables:
            if var.cycle_cde == cycle_code and var.variable_name == variable_name:
                return var.numeric_value
        return 0.0
    

class Tranche(Base):
    """Tranche model - child securities of a Deal."""

    __tablename__ = "tranche"

    dl_nbr: Mapped[int] = mapped_column(ForeignKey("deal.dl_nbr"), primary_key=True)
    tr_id: Mapped[str] = mapped_column(String(15), primary_key=True)
    tr_cusip_id: Mapped[str] = mapped_column(String(14), primary_key=True)

    deal = relationship("Deal", back_populates="tranches")

    tranchebals = relationship(
        "TrancheBal",
        back_populates="tranche",
        primaryjoin=lambda: and_(
            foreign(Tranche.dl_nbr) == TrancheBal.dl_nbr,
            foreign(Tranche.tr_id) == TrancheBal.tr_id,
        ),
        foreign_keys=lambda: [TrancheBal.dl_nbr, TrancheBal.tr_id],
        overlaps="deal,tranches",
    )


class TrancheBal(Base):
    """Tranche balance/historical data."""

    __tablename__ = "tranchebal"

    dl_nbr: Mapped[int] = mapped_column(ForeignKey("tranche.dl_nbr"), primary_key=True)
    tr_id: Mapped[str] = mapped_column(String(15), ForeignKey("tranche.tr_id"), primary_key=True)
    cycle_cde: Mapped[SmallInteger] = mapped_column(SmallInteger, nullable=False, primary_key=True)

    # Financial fields
    tr_end_bal_amt: Mapped[float] = mapped_column(Numeric(19, 4), nullable=False)
    tr_prin_rel_ls_amt: Mapped[float] = mapped_column(Numeric(19, 4), nullable=False)
    tr_pass_thru_rte: Mapped[float] = mapped_column(Float(53), nullable=False)
    tr_accrl_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tr_int_dstrb_amt: Mapped[float] = mapped_column(Numeric(19, 4), nullable=False)
    tr_prin_dstrb_amt: Mapped[float] = mapped_column(Numeric(19, 4), nullable=False)
    tr_int_accrl_amt: Mapped[float] = mapped_column(Numeric(19, 4), nullable=False)
    tr_int_shtfl_amt: Mapped[float] = mapped_column(Numeric(19, 4), nullable=False)

    tranche = relationship(
        "Tranche",
        back_populates="tranchebals",
        primaryjoin=lambda: and_(
            TrancheBal.dl_nbr == foreign(Tranche.dl_nbr),
            TrancheBal.tr_id == foreign(Tranche.tr_id),
        ),
        foreign_keys=lambda: [TrancheBal.dl_nbr, TrancheBal.tr_id],
        overlaps="deal,tranches",
    )


class DealCdiVarRpt(Base):
    """
    Model for deal CDI variable reporting data.
    
    This table stores financial metrics in an EAV (Entity-Attribute-Value) format
    where each row represents a specific CDI variable value for a deal/cycle combination.
    """
    __tablename__ = "deal_cdi_var_rpt"

    # Primary key components
    dl_nbr = Column(Integer, ForeignKey('deal.dl_nbr'), primary_key=True, nullable=False, index=True)  # Added ForeignKey
    cycle_cde = Column(Integer, primary_key=True, nullable=False, index=True) 
    dl_cdi_var_nme = Column(String(32), primary_key=True, nullable=False)
    
    # Value and metadata
    dl_cdi_var_value = Column(String(32), nullable=False)
    lst_upd_dtm = Column(DateTime, nullable=False, server_default=func.now())
    lst_upd_user_id = Column(String(240), nullable=False, server_default='system')
    lst_upd_host_nme = Column(String(40), nullable=False, server_default='localhost')
    timestamp = Column(LargeBinary, nullable=True)  # SQL Server timestamp/rowversion

    # Define relationship to Deal (OPTIONAL - comment out if you don't want relationships)
    deal = relationship("Deal", back_populates="cdi_variables")

    # Indexes for performance (matching your original table structure)
    __table_args__ = (
        # Index on deal number and cycle for common queries
        Index('IX_deal_cdi_var_rpt_dl_nbr_cycle', 'dl_nbr', 'cycle_cde'),
        # Index on variable name for filtering by CDI variable type
        Index('IX_deal_cdi_var_rpt_var_name', 'dl_cdi_var_nme'),
        # Composite index for the most common query pattern
        Index('IX_deal_cdi_var_rpt_composite', 'dl_nbr', 'cycle_cde', 'dl_cdi_var_nme'),
    )

    def __repr__(self):
        return (f"<DealCdiVarRpt(dl_nbr={self.dl_nbr}, cycle={self.cycle_cde}, "
                f"var='{self.dl_cdi_var_nme.strip()}', value='{self.dl_cdi_var_value.strip()}')>")

    @property
    def variable_name(self) -> str:
        """Get the variable name with whitespace trimmed"""
        return self.dl_cdi_var_nme.strip() if self.dl_cdi_var_nme else ""

    @property
    def variable_value(self) -> str:
        """Get the variable value with whitespace trimmed"""
        return self.dl_cdi_var_value.strip() if self.dl_cdi_var_value else ""

    @property
    def numeric_value(self) -> float:
        """
        Convert the variable value to a numeric value.
        Handles comma-separated numbers like '1,055,732.79'.
        Returns 0.0 if conversion fails.
        """
        try:
            # Remove commas and trim whitespace before converting to float
            clean_value = self.variable_value.replace(',', '').strip()
            return float(clean_value)
        except (ValueError, TypeError, AttributeError):
            return 0.0

    def matches_pattern(self, pattern: str, tranche_suffix: str) -> bool:
        """
        Check if this CDI variable matches a given pattern with tranche suffix.
        
        Args:
            pattern: Pattern like "#RPT_RRI_{tranche_suffix}"
            tranche_suffix: Suffix like "M1", "B1", etc.
            
        Returns:
            True if this variable matches the pattern
        """
        expected_name = pattern.replace("{tranche_suffix}", tranche_suffix)
        return self.variable_name == expected_name

    @classmethod
    def get_by_pattern_and_cycle(cls, session, pattern: str, tranche_mappings: dict, 
                                cycle_code: int, deal_numbers: list = None):
        """
        Query CDI variables that match a specific pattern and tranche mappings.
        
        Args:
            session: SQLAlchemy session
            pattern: Variable pattern like "#RPT_RRI_{tranche_suffix}"
            tranche_mappings: Dict mapping suffixes to tr_id lists
            cycle_code: Cycle code to filter by
            deal_numbers: Optional list of deal numbers to filter by
            
        Returns:
            Query object that can be executed
        """
        from sqlalchemy import or_
        
        # Build list of variable names to search for
        variable_names = []
        for suffix in tranche_mappings.keys():
            var_name = pattern.replace("{tranche_suffix}", suffix)
            variable_names.append(var_name)
        
        query = session.query(cls).filter(
            cls.cycle_cde == cycle_code,
            cls.dl_cdi_var_nme.in_(variable_names)
        )
        
        if deal_numbers:
            query = query.filter(cls.dl_nbr.in_(deal_numbers))
            
        return query

    @classmethod
    def get_for_deals_and_cycle(cls, session, deal_numbers: list, cycle_code: int):
        """
        Get all CDI variables for specific deals and cycle.
        
        Args:
            session: SQLAlchemy session
            deal_numbers: List of deal numbers
            cycle_code: Cycle code
            
        Returns:
            Query object
        """
        return session.query(cls).filter(
            cls.dl_nbr.in_(deal_numbers),
            cls.cycle_cde == cycle_code
        )

    @classmethod
    def get_variable_names_for_pattern(cls, session, pattern_prefix: str, 
                                     cycle_code: int = None):
        """
        Get all variable names that start with a pattern prefix.
        Useful for discovering available CDI variables.
        
        Args:
            session: SQLAlchemy session  
            pattern_prefix: Prefix like "#RPT_RRI_"
            cycle_code: Optional cycle code to filter by
            
        Returns:
            List of distinct variable names
        """
        query = session.query(cls.dl_cdi_var_nme.distinct()).filter(
            cls.dl_cdi_var_nme.like(f"{pattern_prefix}%")
        )
        
        if cycle_code:
            query = query.filter(cls.cycle_cde == cycle_code)
            
        return [name.strip() for name, in query.all()]


class DealAttr(Base):
    """Deal attributes table for storing key-value pairs of deal metadata."""

    __tablename__ = "deal_attr"

    dl_nbr: Mapped[int] = mapped_column(ForeignKey("deal.dl_nbr"), primary_key=True)
    abr_cde: Mapped[str] = mapped_column(String(50), primary_key=True)  # Attribute code
    dl_attr_value: Mapped[str] = mapped_column(String(255), nullable=True)  # Attribute value
    
    # Optional metadata
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship back to deal
    deal = relationship("Deal", back_populates="attributes")

    def __repr__(self):
        return f"<DealAttr(dl_nbr={self.dl_nbr}, code='{self.abr_cde}', value='{self.dl_attr_value}')>"
