from abc import ABC
from concrete import fhe
import numpy as np
import numbers

from concrete_biopython.SeqWrapper import SeqWrapper

Tracer = fhe.tracing.tracer.Tracer

_NOT_IMPLEMENTED_FHE =  Exception('This function is not compatible with FHE')

class _FheSeqAbstractBaseClass(ABC):
    """
    The FHE version Bio.Seq._SeqAbstractBaseClass abstract class

    Methods from Bio.Seq._SeqAbstractBaseClass that cannot be implemented in fhe:
    split, rsplit, strip, lstrip, rstrip


    Dev notes :
    -----------
    
    TODO:

    # Hard to implement in fhe (if doable):
    count, count_overlap , __contains__ , find , rfind , index , rindex, replace

    # Cannot be implemented, because it collides with array __add__ function:
    __radd__

    # Require compatible implementaion of numpy.repeat for concrete to be done properly
    __mul__ , __rmul__ , __imul__

    # Unused for now because all characters are uppercase
    #   but lower case characters could easily be added to SeqWrapper.LETTERS
    upper , lower , isupper , islower

    # If the class is extended to include undefined sequences:
    defined , defined_ranges

    """

    def __init__(self, data, length=None):
        if data is None:
            if length is None:
                raise ValueError("length must not be None if data is None")
            elif length == 0:
                self._data = fhe.zeros(0)
            elif length < 0:
                raise ValueError("length must not be negative.")
            else:
                #self._data = _UndefinedSequenceData(length)
                raise NotImplemented
        elif isinstance(data, Tracer):
            if data.size>1:
                self._data = data[:] # take a copy
            elif data.size==1:
                try:
                    self._data = data[:].reshape(1) # take a copy if array of size 1
                except:
                    self._data = data.reshape(1) # just copy value if isolated value
            else:
                self._data = fhe.zeros(0)
        elif isinstance(data, _FheSeqAbstractBaseClass):
            if data._data.size>1:
                self._data = data._data[:] # take a copy
            elif data._data.size==1:
                self._data = data._data[:].reshape(1)  # take a copy
            else:
                self._data = fhe.zeros(0) 
        else:
            raise TypeError(
                "data should be either a concrete.fhe.tracing.tracer.Tracer object or a _FheSeqAbstractBaseClass object"
            )    


    def toArray(self):
        return self._data

    def __eq__(self, other):
        """Compare the sequence to another sequence or an array.

        Sequences are equal to each other if their sequence contents is identical
        """
        if isinstance(other, _FheSeqAbstractBaseClass):
            other = other._data
        elif isinstance(other, Tracer):
            pass
        else:
            raise NotImplementedError

        if len(self) != other.size:
            return fhe.zeros(1)[0] # return False if the lengths are different
        else:
            return (len(self) - np.sum(self._data == other))==0


    def __lt__(self, other):
        """ Computes wether a sequence is lower than another, in alphabetical order

        A sequence A is lower than a sequence B if and only if:
        there exist an index i such that: A[i] < B[i]  AND  for all k<i, A[k] <= B[k]

        If sequence have different length, the shorter one is considered to have extra empty characters
        where the empty character is the lowest in alphabetical order
        """
        # prepare arrays if they have different size
        difflen = len(other) - len(self)
        
        # append a zero to the shortest sequence and crop the other one
        # zero is always <= to any other character so no need to append more zeros
        if difflen > 0:
            A = np.concatenate((self._data, fhe.zeros(1).reshape(1)), axis=0)
            B = other._data[0:A.size]
        elif difflen <0:
            B = np.concatenate((other._data, fhe.zeros(1).reshape(1)), axis=0)
            A = self._data[0:B.size]
        else:
            A=self._data[:]  # copy array
            B=other._data[:] # copy array

        n = A.size

        if n==0:
            return fhe.ones(1)[0] # special case if both arrays are empty

        # Fast computation of (A < B)
        # (This algorithm is inspired from the behavior of the failure of subtraction(A,B) algorithm when A < B)
        borrow = 0
        for i in range(n):
            # report borrow
            borrow = A[-i-1] - B[-i-1] - borrow < 0
        
        # When A < B, subtracting B from A fails and overflows, we use the overflow value borrow to know if A < B
        return borrow


    def __le__(self, other):
        """ Computes wether a sequence is lower or equal than another, in alphabetical order

        The proposition "A <= B" is equivalent to "not (B < A)" (see self.__lt__)

        If sequence have different length, the shorter one is considered to have extra empty characters
        where the empty character is the lowest in alphabetical order
        """       
        return 1-(other < self)

    def __gt__(self, other):
        """ Computes wether a sequence is greater than another, in alphabetical order

        The proposition "A > B" is the symetry of "B < A" (see self.__lt__)

        If sequence have different length, the shorter one is considered to have extra empty characters
        where the empty character is the lowest in alphabetical order
        """
        return other < self

    def __ge__(self, other):
        """ Computes wether a sequence is greater or equal than another, in alphabetical order

        The proposition "A >= B" is equivalent to of "not (A < B)" (see self.__lt__)

        If sequence have different length, the shorter one is considered to have extra empty characters
        where the empty character is the lowest in alphabetical order
        """       
        return 1-(self < other)

    def __len__(self):
        """Return the length of the sequence."""
        return self._data.size

    def __iter__(self):
        """Return an iterable of the sequence."""
        return iter(self._data)

    def __getitem__(self, index):
        """Return a subsequence as a single integer or as a sequence object.
        """
        if isinstance(index, numbers.Integral):
            # Return a single integer
            return self._data[index]
        elif isinstance(index, Tracer):
            if index.size==1:
                # If single encrypted index
                index = (index + len(self)) % len(self) # in case the index is negative
                return np.sum(self._data*(np.arange(len(self))==index))
            else:
                raise NotImplementedError
        else:
            # Return the (sub)sequence as another Seq/MutableSeq object
            return self.__class__(self._data[index])

    def __add__(self, other):
        """Add a sequence or array to this sequence.
        """
        if isinstance(other, _FheSeqAbstractBaseClass):
            return self.__class__(np.concatenate((self._data, other._data), axis=0)) # np.concatenate will deep copy arrays
        elif isinstance(other, Tracer):
            return self.__class__(np.concatenate((self._data, other), axis=0))
        else:
            raise NotImplementedError

    def startswith(self, prefix, start=None, end=None):
        """Return True if data starts with the specified prefix, False otherwise.

        With optional start, test data beginning at that position.
        With optional end, stop comparing data at that position.
        prefix can also be a tuple of bytes to try.
        """
        if isinstance(prefix,_FheSeqAbstractBaseClass):
            l=len(prefix)
        elif isinstance(prefix, Tracer):
            l=prefix.size
        else:
            raise NotImplementedError

        if start and end:
            return self[start:end] == prefix
        elif start:
            return self[start:start+l] == prefix
        elif end:
            return self[0:np.min((l,end))] == prefix
        else:
            return self[0:l] == prefix

    def endswith(self, suffix, start=None, end=None):
        """Return True if data ends with the specified suffix, False otherwise.

        With optional start, test data beginning at that position.
        With optional end, stop comparing data at that position.
        suffix can also be a tuple of bytes to try.
        """
        if isinstance(suffix,_FheSeqAbstractBaseClass):
            l=len(suffix)
        elif isinstance(suffix, Tracer):
            l=suffix.size
        else:
            raise NotImplementedError

        if start and end:
            return self[start:end] == suffix
        elif start:
            return self[np.max((start,len(self)-l)):] == suffix
        elif end:
            return self[end-l:end] == suffix
        else:
            return self[len(self)-l:] == suffix

    def split(self, sep=None, maxsplit=-1):
        raise _NOT_IMPLEMENTED_FHE

    def rsplit(self, sep=None, maxsplit=-1):
        raise _NOT_IMPLEMENTED_FHE

    def strip(self, chars=None):
        raise _NOT_IMPLEMENTED_FHE

    def lstrip(self, chars=None):
        raise _NOT_IMPLEMENTED_FHE

    def rstrip(self, chars=None):
        raise _NOT_IMPLEMENTED_FHE

    def translate(self, table="Standard"):
        """Turn a nucleotide sequence into a protein sequence by creating a new sequence object.

        This method will translate DNA or RNA sequences. It should not
        be used on protein sequences as any result will be biologically
        meaningless.

        Arguments:
         - table - Which codon table to use?  This can be either a name
           (string), or a fhe.LookupTable object (useful for non-standard genetic codes).
           This defaults to the "Standard" table.
        """
        n = len(self)

        if n % 3 != 0:
            raise Error(
                "Partial codon, len(sequence) not a multiple of three. "
            )

        # first of all, reduce the integers of letters 'ACGU' (and T treated as a U) to 0,1,2,3
        translationReductionTable = fhe.LookupTable(SeqWrapper.get_translationReductionTable())
        reduced_integers = translationReductionTable[self._data]

        # compute codon indices from first, second and third letters
        codon_indices = reduced_integers[0::3]*16 + reduced_integers[1::3]*4 + reduced_integers[2::3]

        # apply translation of the codons by their index in the translation table
        translationTable = fhe.LookupTable(SeqWrapper.get_translationTable(table))        
        protein_seq = translationTable[codon_indices]

        return self.__class__(protein_seq)


    def complement(self, inplace=False):
        """Return the complement as an RNA sequence.

        Any T in the sequence is treated as a U
        Any other letter than ACGT will be changed to the character with index 0 which should not be done

        The sequence is modified in-place and returned if inplace is True

        As ``Seq`` objects are immutable, a ``TypeError`` is raised if
        ``complement_rna`` is called on a ``Seq`` object with ``inplace=True``.
        """
        DNAcomplementTable = fhe.LookupTable(SeqWrapper.get_DNA_complementTable()) 
        complement_seq = DNAcomplementTable[self._data]
        if inplace:
            if self.__class__ == FheSeq:
                raise TypeError("Sequence is immutable")
            self._data = complement_seq
            return self
        else:
            return self.__class__(complement_seq)

    def complement_rna(self, inplace=False):
        """Return the complement as an RNA sequence.

        Any T in the sequence is treated as a U

        As ``Seq`` objects are immutable, a ``TypeError`` is raised if
        ``complement_rna`` is called on a ``Seq`` object with ``inplace=True``.
        """
        RNAcomplementTable = fhe.LookupTable(SeqWrapper.get_RNA_complementTable()) 
        complement_seq = RNAcomplementTable[self._data]
        if inplace:
            if self.__class__ == FheSeq:
                raise TypeError("Sequence is immutable")
            self._data = complement_seq
            return self
        else:
            return self.__class__(complement_seq)

    def reverse_complement(self, inplace=False):
        """Return the reverse complement as a DNA sequence.

        Any U in the sequence is treated as a T

        The sequence is modified in-place and returned if inplace is True

        As ``Seq`` objects are immutable, a ``TypeError`` is raised if
        ``reverse_complement`` is called on a ``Seq`` object with
        ``inplace=True``.
        """        
        reverse_complement = self.complement(inplace)
        if inplace:
            if not isinstance(self, FheSeq):
                raise TypeError("Sequence is immutable")
        reverse_complement._data[::-1] = reverse_complement._data
        return reverse_complement

    def reverse_complement_rna(self, inplace=False):
        """Return the reverse complement as an RNA sequence.

        The sequence is modified in-place and returned if inplace is True

        As ``Seq`` objects are immutable, a ``TypeError`` is raised if
        ``reverse_complement_rna`` is called on a ``Seq`` object with
        ``inplace=True``.
        """
        reverse_complement_rna = self.complement_rna(inplace)
        if inplace:
            if not isinstance(self, FheSeq):
                raise TypeError("Sequence is immutable")
        reverse_complement_rna._data[::-1] = reverse_complement_rna._data
        return reverse_complement_rna

    def transcribe(self, inplace=False):
        """Transcribe a DNA sequence into RNA and return the RNA sequence as a new Seq object.

        As ``Seq`` objects are immutable, a ``TypeError`` is raised if
        ``transcribe`` is called on a ``Seq`` object with ``inplace=True``.

        Trying to transcribe an RNA sequence has no effect.
        If you have a nucleotide sequence which might be DNA or RNA
        (or even a mixture), calling the transcribe method will ensure
        any T becomes U.

        Trying to transcribe a protein sequence will replace any
        T for Threonine with U for Selenocysteine, which has no
        biologically plausible rational.
        """
        transcriptionTable = fhe.LookupTable(SeqWrapper.get_transcriptionTable()) 
        transcribed_seq = transcriptionTable[self._data]
        if inplace:
            if self.__class__ == FheSeq:
                raise TypeError("Sequence is immutable")
            self._data = transcribed_seq
            return self
        else:
            return self.__class__(transcribed_seq)

    def back_transcribe(self, inplace=False):
        """Return the DNA sequence from an RNA sequence by creating a new Seq object.

        The sequence is modified in-place and returned if inplace is True:

        As ``Seq`` objects are immutable, a ``TypeError`` is raised if
        ``transcribe`` is called on a ``Seq`` object with ``inplace=True``.

        Trying to back-transcribe DNA has no effect, If you have a nucleotide
        sequence which might be DNA or RNA (or even a mixture), calling the
        back-transcribe method will ensure any U becomes T.

        Trying to back-transcribe a protein sequence will replace any U for
        Selenocysteine with T for Threonine, which is biologically meaningless.
        """
        backTranscriptionTable = fhe.LookupTable(SeqWrapper.get_back_transcriptionTable())
        back_transcribed_seq = backTranscriptionTable[self._data]
        if inplace:
            if self.__class__ == FheSeq:
                raise TypeError("Sequence is immutable")
            self._data = back_transcribed_seq
            return self
        else:
            return self.__class__(back_transcribed_seq)

    def join(self, other):
        """Return a merge of the sequences in other, spaced by the sequence from self.

        Accepts a FheSeq object, FheMutableSeq object, or array (and iterates over
        the integers), or an iterable containing Seq, MutableSeq, or string
        objects. These arguments will be concatenated with the calling sequence
        as the spacer:
        """
        joindata = []
        if isinstance(other, _FheSeqAbstractBaseClass):
            for i in range(len(other)):
                joindata.append(other[i].reshape(1))
        elif isinstance(other, Tracer):
            for i in range(other.size):
                joindata.append(other[i].reshape(1))
        elif isinstance(other, list) or isinstance(other, tuple):
            for data in other:
                if isinstance(data, _FheSeqAbstractBaseClass):
                    joindata.append(data.toArray())
                elif isinstance(data, Tracer):
                    joindata.append(data)
                else:
                    raise TypeError('list must contain _FheSeqAbstractBaseClass or concrete.fhe.tracing.tracer.Tracer objetcs')
        else:
            raise TypeError('data type must be _FheSeqAbstractBaseClass or concrete.fhe.tracing.tracer.Tracer')

        concatenation = joindata[0]
        for i in range(1,len(joindata)):
            concatenation = np.concatenate((concatenation,self._data,joindata[i]),axis=0)

        return self.__class__(concatenation)


class FheSeq(_FheSeqAbstractBaseClass):
    """
    The FHE version Bio.Seq.Seq class

    Dev notes:
    ----------
    
    TODO:

    __hash__

    """
    def __init__(self, data, length=None):
        super().__init__(data, length)


class FheMutableSeq(_FheSeqAbstractBaseClass):
    """
    The FHE version Bio.Seq.MutableSeq class

    This method from Bio.Seq.FheMutableSeq that cannot be implemented in fhe: remove
    """
    def __init__(self, data, length=None):
        super().__init__(data, length)

    def reverse(self):
        s=len(self)
        reverse_seq = fhe.zeros(s)
        for i in range(s):
            reverse_seq[i] = self._data[s-i-1]
        self._data = reverse_seq

    def __setitem__(self, index, value):
        """Set a subsequence of single letter via value parameter.
        """
        if isinstance(index, numbers.Integral):
            # Replacing a single letter with a new string
            self._data[index] = value
        else:
            # Replacing a sub-sequence
            if isinstance(value, _FheSeqAbstractBaseClass):
                self._data[index] = value._data
            elif isinstance(value, Tracer):
                self._data[index] = value
            else:
                raise TypeError(f"received unexpected type '{type(value).__name__}'")

    def __delitem__(self, index):
        """Delete a subsequence of single letter.
        """
        if isinstance(index, numbers.Integral):
            # Replacing a single letter with a new string
            if(index > 0 or index <-1):
                self._data = (self[0:index]+self[index+1:])._data
            elif index==0:
                self._data = self[1:]._data
            else: #-1
                self._data = self[0:index]._data
        else:
            self._data = (self[0:index.start]+self[index.stop:])._data

    def append(self, c):
        """Add a single letter to the mutable sequence object.
        No return value.
        """
        if not isinstance(c, Tracer):
            raise TypeError('c must be of type Tracer')
        if c.size > 1:
            raise ValueError('c must be of size 1')
        self._data = (self+c.reshape(1))._data

    def insert(self, i, c):
        """Add a single letter to the mutable sequence object at a given index.
        No return value.
        """
        if not isinstance(c, Tracer):
            raise TypeError('c must be of type Tracer')
        if c.size > 1:
            raise ValueError('c must be of size 1')
        self._data = (self[0:i]+c.reshape(1)+self[i:])._data

    def pop(self, i=-1):
        """Remove a subsequence of a single letter at given index.
        Returns the last character of the sequence.
        """
        c = self._data[i]
        self.__delitem__(i)
        return c
    
    def extend(self, other):
        """Add a sequence to the original mutable sequence object.
        No return value.
        """
        if isinstance(other, _FheSeqAbstractBaseClass) or isinstance(other,Tracer):
            self._data = (self+other)._data
        else:
            raise TypeError("expected a string, Seq or MutableSeq")

